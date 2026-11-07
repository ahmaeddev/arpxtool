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
结果2 = '\x1b['

class 缓存3:
    enabled = sys.stdout.isatty()
    truecolor = False
    width = 88

    @classmethod
    def probe(cls):
        cls.width = shutil.get_terminal_size((88, 24)).columns
        if os.environ.get('NO_COLOR') is not None:
            cls.enabled = False
        参数801 = os.environ.get('TERM', '')
        if 参数801 == 'dumb':
            cls.enabled = False
        缓存1323 = os.environ.get('COLORTERM', '').lower()
        cls.truecolor = 缓存1323 in ('truecolor', '24bit') or 'truecolor' in 参数801
        if not cls.enabled:
            cls.truecolor = False

    @classmethod
    def clamp(cls, 行905, 列906):
        return max(行905, min(列906, cls.width))

class 索引4:
    RESET = 结果2 + '0m'
    BOLD = 结果2 + '1m'
    DIM = 结果2 + '2m'
    ITALIC = 结果2 + '3m'
    HIDE = 结果2 + '?25l'
    SHOW = 结果2 + '?25h'
    CLR = 结果2 + 'K'
    HOME = 结果2 + 'H'
    WIPE = 结果2 + '2J' + 结果2 + 'H'

    def __init__(self, 字节907, 栈699=False):
        self.rgb = 字节907
        self.bold = 栈699
        self._cache = {}

    def code(self):
        if not 缓存3.enabled:
            return 索引4.BOLD if self.bold else ''
        if self.rgb in self._cache:
            return self._cache[self.rgb]
        名字909, 检查910, 映射692 = self.rgb
        if 缓存3.truecolor:
            节点697 = f'{结果2}{(1 if self.bold else 22)};38;2;{名字909};{检查910};{映射692}m'
        else:
            节点697 = f'{结果2}{(1 if self.bold else 22)};38;5;{索引4.nearest256(名字909, 检查910, 映射692)}m'
        self._cache[self.rgb] = 节点697
        return 节点697

    def __call__(self, text):
        if not 缓存3.enabled:
            return str(text)
        return f'{self.code()}{text}{索引4.RESET}'

    @staticmethod
    def bg(字节907, 文本908=None):
        if not 缓存3.enabled:
            return lambda 条目693: str(条目693)
        文本908 = 文本908 or (241, 245, 249)
        名字909, 检查910, 映射692 = 字节907
        if 缓存3.truecolor:
            code = f'{结果2}48;2;{名字909};{检查910};{映射692}m{结果2}38;2;{文本908[0]};{文本908[1]};{文本908[2]}m{结果2}1m'
        else:
            code = f'{结果2}48;5;{索引4.nearest256(名字909, 检查910, 映射692)}m{结果2}38;5;{索引4.nearest256(*文本908)}m{结果2}1m'
        return lambda 条目693: f'{code} {条目693} {索引4.RESET}'

    @staticmethod
    def nearest256(名字909, 检查910, 映射692):
        报告719 = (0, 95, 135, 175, 215, 255)

        def 文本1588(步骤818):
            写入1031, 关闭1674 = (0, 10 ** 9)
            for 读取912, 节点697 in enumerate(报告719):
                行785 = abs(节点697 - 步骤818)
                if 行785 < 关闭1674:
                    关闭1674, 写入1031 = (行785, 读取912)
            return 写入1031
        修补1558, 报告1559, 变量1560 = (文本1588(名字909), 文本1588(检查910), 文本1588(映射692))
        索引1324 = 16 + 36 * 修补1558 + 6 * 报告1559 + 变量1560
        计数1325 = (名字909 + 检查910 + 映射692) // 3
        路径1326 = max(0, min(23, (计数1325 - 8) // 10))
        列表1327 = 8 + 10 * 路径1326
        数据1328 = (报告719[修补1558] - 名字909) ** 2 + (报告719[报告1559] - 检查910) ** 2 + (报告719[变量1560] - 映射692) ** 2
        状态1329 = (列表1327 - 名字909) ** 2 + (列表1327 - 检查910) ** 2 + (列表1327 - 映射692) ** 2
        return 索引1324 if 数据1328 <= 状态1329 else 232 + 路径1326

class 计数5:
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

def 路径6(队列691, 映射692, 条目693):
    return 队列691 + (映射692 - 队列691) * 条目693

def 列表7(偏移694, 区块695, 条目693):
    return (int(路径6(偏移694[0], 区块695[0], 条目693)), int(路径6(偏移694[1], 区块695[1], 条目693)), int(路径6(偏移694[2], 区块695[2], 条目693)))

def 数据8(句柄696, 条目693):
    条目693 = max(0.0, min(1.0, 条目693))
    if len(句柄696) == 1:
        return 句柄696[0]
    键943 = 1.0 / (len(句柄696) - 1)
    读取912 = min(int(条目693 / 键943), len(句柄696) - 2)
    表944 = (条目693 - 读取912 * 键943) / 键943
    return 列表7(句柄696[读取912], 句柄696[读取912 + 1], 表944)
状态9 = (120, 235, 255)
标记10 = (34, 211, 238)
队列11 = (56, 132, 255)
映射12 = (139, 92, 246)
条目13 = (232, 121, 249)
偏移14 = (251, 113, 133)
区块15 = (251, 191, 36)
句柄16 = (163, 230, 53)
节点17 = (52, 211, 153)
步骤18 = (45, 212, 191)
栈19 = (148, 163, 184)
源20 = (100, 116, 139)
目标21 = (51, 65, 85)
值22 = (241, 245, 249)
键23 = (248, 113, 113)
表24 = (226, 232, 240)
行25 = [标记10, 队列11, 映射12, 条目13]
列26 = [步骤18, 标记10, 队列11]
字节27 = [区块15, 偏移14, 条目13]
文本28 = [节点17, 步骤18, 标记10]
名字29 = [区块15, 偏移14]
检查30 = [键23, 条目13]
写入31 = 索引4(标记10, True)
读取32 = 索引4(状态9, True)
打开33 = 索引4(源20)
关闭34 = 索引4(节点17, True)
构建35 = 索引4(区块15, True)
解析36 = 索引4(键23, True)
扫描37 = 索引4(队列11)
修补38 = 索引4(表24)
报告39 = 索引4(映射12, True)
变量40 = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
参数41 = ['⣾', '⣽', '⣻', '⢿', '⡿', '⣟', '⣯', '⣷']
结果42 = ' ▏▎▍▌▋▊▉█'
缓存43 = '━'
索引44 = '─'
计数45 = ('╭', '╮', '╰', '╯', '│', '─')
路径46 = '▸'
列表47 = '→'
数据48 = '✓'
状态49 = '✗'
标记50 = '·'
队列51 = '!'
映射52 = '◆'
条目53 = '●'
偏移54 = '○'

def 区块55(节点697):
    return len(re.sub('\\033\\[[0-9;?]*[A-Za-z]', '', 节点697))

def 句柄56(节点697, 步骤698):
    return 节点697 + ' ' * max(0, 步骤698 - 区块55(节点697))

def 节点57(节点697, 步骤698):
    节点697 = re.sub('\\033\\[[0-9;?]*[A-Za-z]', '', str(节点697))
    return 节点697 if len(节点697) <= 步骤698 else 节点697[:max(0, 步骤698 - 1)] + '…'

class 步骤58:
    height = 0

    @classmethod
    def paint(cls, 值702):
        if not 缓存3.enabled:
            for 名字949 in 值702:
                sys.stdout.write(名字949 + '\n')
            sys.stdout.flush()
            return
        if cls.height:
            sys.stdout.write(f'{结果2}{cls.height}A')
        for 读取912 in range(max(cls.height, len(值702))):
            sys.stdout.write(结果2 + '2K' + (值702[读取912] if 读取912 < len(值702) else ''))
            sys.stdout.write('\r\n')
        cls.height = len(值702)
        sys.stdout.flush()

    @classmethod
    def close(cls):
        cls.height = 0

def 栈59(text, 句柄696, 栈699=False):
    if not 缓存3.enabled:
        return text
    步骤698 = max(1, len(text) - 1)
    文本708 = []
    for 读取912, 目标701 in enumerate(text):
        if 目标701 == ' ':
            文本708.append(目标701)
            continue
        文本708.append(索引4(数据8(句柄696, 读取912 / 步骤698), 栈699)(目标701))
    return ''.join(文本708)

def 源60(width, 句柄696, 目标701=缓存43):
    if not 缓存3.enabled:
        return 目标701 * width
    文本708 = []
    for 读取912 in range(width):
        文本708.append(索引4(数据8(句柄696, 读取912 / max(1, width - 1)))(目标701))
    return ''.join(文本708)

def 目标61(width=None, 句柄696=None, 目标701=缓存43):
    列946 = width or 缓存3.clamp(30, 84)
    return 源60(列946, 句柄696 or 行25, 目标701)

def 值62(值702, 句柄696=None, 键703=None, width=None):
    句柄696 = 句柄696 or 列26
    字节947 = max([区块55(目标1421) for 目标1421 in 值702] + [0])
    if 键703:
        字节947 = max(字节947, 区块55(键703) + 4)
    列946 = 字节947 if width is None else max(字节947, width)
    列946 = min(列946, 缓存3.clamp(40, 92))
    标记1330, 队列1331, 映射1332, 条目1333, 步骤818, 解析956 = 计数45
    文本948 = lambda 条目693: 索引4(句柄696[-1])(条目693) if 缓存3.enabled else 条目693
    文本708 = []
    if 键703:
        修补718 = ' ' + 键703 + ' '
        偏移1334 = max(0, (列946 - 区块55(修补718)) // 2)
        文本708.append(文本948(标记1330 + 解析956 * 偏移1334) + 索引4(状态9, True)(修补718) + 文本948(解析956 * (列946 - 区块55(修补718) - 偏移1334) + 队列1331))
    else:
        文本708.append(文本948(标记1330 + 解析956 * 列946 + 队列1331))
    for 名字949 in 值702:
        文本708.append(文本948(步骤818) + 句柄56(名字949, 列946) + 文本948(步骤818))
    文本708.append(文本948(映射1332 + 解析956 * 列946 + 条目1333))
    return 文本708

class 键63:

    @staticmethod
    def blank():
        print()

    @staticmethod
    def head(键703, 句柄696=None):
        句柄696 = 句柄696 or 行25
        计数5.begin(键703)
        print()
        print('  ' + 目标61(缓存3.clamp(20, 78), 句柄696, 索引44))
        步骤698 = len(计数5.records) + 1
        区块1335 = 索引4.bg(句柄696[-1], 目标21)(' %02d ' % 步骤698)
        修补718 = f'{路径46} {键703.upper()}'
        if 缓存3.enabled:
            print('  ' + 区块1335 + ' ' + 索引4(状态9, True)(修补718))
        else:
            print('  %02d %s' % (步骤698, 修补718))
        print('  ' + 目标61(缓存3.clamp(20, 78), 句柄696, 索引44))

    @staticmethod
    def ok(表704):
        行345('ok', 表704)
        print('  ' + 关闭34(数据48) + ' ' + 修补38(表704))

    @staticmethod
    def bad(表704):
        行345('bad', 表704)
        print('  ' + 解析36(状态49) + ' ' + 修补38(表704))

    @staticmethod
    def warn(表704):
        行345('warn', 表704)
        print('  ' + 构建35(队列51) + ' ' + 修补38(表704))

    @staticmethod
    def info(表704):
        行345('info', 表704)
        print('  ' + 扫描37(列表47) + ' ' + 打开33(表704))

    @staticmethod
    def kv(key, 标记730, width=22, 写入791=None):
        名字989 = 打开33(key.ljust(width))
        步骤818 = (写入791 or 修补38)(str(标记730))
        print(f'  {名字989}{步骤818}')

    @staticmethod
    def bullet(表704, 写入791=None):
        print('  ' + (写入791 or 报告39)(映射52) + ' ' + 打开33(表704))

    @staticmethod
    def bar(修补718, 标记730, total, width=26, 句柄696=None):
        句柄696 = 句柄696 or 文本28
        total = max(1, total)
        句柄1336 = max(0.0, min(1.0, 标记730 / total))
        节点1337 = 句柄1336 * width
        句柄1256 = int(节点1337)
        步骤1338 = 节点1337 - 句柄1256
        列表847 = '█' * 句柄1256
        if 句柄1256 < width:
            列表847 += 结果42[int(步骤1338 * 8)]
            列表847 += '░' * (width - 句柄1256 - 1)
        if 缓存3.enabled:
            列表847 = 栈59(列表847, 句柄696)
        扫描1077 = f'{句柄1336 * 100:5.1f}%'
        print(f'  {打开33(修补718.ljust(18))}{列表847} {修补38(扫描1077)}')

    @staticmethod
    def spark(写入911, 句柄696=None):
        关闭954 = '▁▂▃▄▅▆▇█'
        if not 写入911:
            return ''
        行905, 列906 = (min(写入911), max(写入911))
        键943 = 列906 - 行905 or 1
        节点697 = ''.join((关闭954[min(7, int((步骤818 - 行905) / 键943 * 7))] for 步骤818 in 写入911))
        return 栈59(节点697, 句柄696 or 列26) if 缓存3.enabled else 节点697
表64 = {'A': (' █████╗ ', '██╔══██╗', '███████║', '██╔══██║', '██║  ██║', '╚═╝  ╚═╝'), 'B': ('██████╗ ', '██╔══██╗', '██████╔╝', '██╔══██╗', '██████╔╝', '╚═════╝ '), 'C': (' ██████╗', '██╔════╝', '██║     ', '██║     ', '╚██████╗', ' ╚═════╝'), 'D': ('██████╗ ', '██╔══██╗', '██║  ██║', '██║  ██║', '██████╔╝', '╚═════╝ '), 'E': ('███████╗', '██╔════╝', '█████╗  ', '██╔══╝  ', '███████╗', '╚══════╝'), 'F': ('███████╗', '██╔════╝', '█████╗  ', '██╔══╝  ', '██║     ', '╚═╝     '), 'G': (' ██████╗ ', '██╔════╝ ', '██║  ███╗', '██║   ██║', '╚██████╔╝', ' ╚═════╝ '), 'H': ('██╗  ██╗', '██║  ██║', '███████║', '██╔══██║', '██║  ██║', '╚═╝  ╚═╝'), 'I': ('██╗', '██║', '██║', '██║', '██║', '╚═╝'), 'J': ('     ██╗', '     ██║', '     ██║', '██   ██║', '╚█████╔╝', ' ╚════╝ '), 'K': ('██╗  ██╗', '██║ ██╔╝', '█████╔╝ ', '██╔═██╗ ', '██║  ██╗', '╚═╝  ╚═╝'), 'L': ('██╗     ', '██║     ', '██║     ', '██║     ', '███████╗', '╚══════╝'), 'M': ('███╗   ███╗', '████╗ ████║', '██╔████╔██║', '██║╚██╔╝██║', '██║ ╚═╝ ██║', '╚═╝     ╚═╝'), 'N': ('███╗   ██╗', '████╗  ██║', '██╔██╗ ██║', '██║╚██╗██║', '██║ ╚████║', '╚═╝  ╚═══╝'), 'O': (' ██████╗ ', '██╔═══██╗', '██║   ██║', '██║   ██║', '╚██████╔╝', ' ╚═════╝ '), 'P': ('██████╗ ', '██╔══██╗', '██████╔╝', '██╔═══╝ ', '██║     ', '╚═╝     '), 'Q': (' ██████╗ ', '██╔═══██╗', '██║   ██║', '██║▄▄ ██║', '╚██████╔╝', ' ╚══▀▀═╝ '), 'R': ('██████╗ ', '██╔══██╗', '██████╔╝', '██╔══██╗', '██║  ██║', '╚═╝  ╚═╝'), 'S': ('███████╗', '██╔════╝', '███████╗', '╚════██║', '███████║', '╚══════╝'), 'T': ('████████╗', '╚══██╔══╝', '   ██║   ', '   ██║   ', '   ██║   ', '   ╚═╝   '), 'U': ('██╗   ██╗', '██║   ██║', '██║   ██║', '██║   ██║', '╚██████╔╝', ' ╚═════╝ '), 'V': ('██╗   ██╗', '██║   ██║', '██║   ██║', '╚██╗ ██╔╝', ' ╚████╔╝ ', '  ╚═══╝  '), 'W': ('██╗    ██╗', '██║    ██║', '██║ █╗ ██║', '██║███╗██║', '╚███╔███╔╝', ' ╚══╝╚══╝ '), 'X': ('██╗  ██╗', '╚██╗██╔╝', ' ╚███╔╝ ', ' ██╔██╗ ', '██╔╝ ██╗', '╚═╝  ╚═╝'), 'Y': ('██╗   ██╗', '╚██╗ ██╔╝', ' ╚████╔╝ ', '  ╚██╔╝  ', '   ██║   ', '   ╚═╝   '), 'Z': ('███████╗', '╚══███╔╝', '  ███╔╝ ', ' ███╔╝  ', '███████╗', '╚══════╝'), ' ': ('  ', '  ', '  ', '  ', '  ', '  '), '-': ('      ', '      ', '█████╗', '╚════╝', '      ', '      '), '.': ('  ', '  ', '  ', '  ', '██╗', '╚═╝')}

def 行65(text):
    打开793 = [''] * 6
    for 目标701 in text.upper():
        栈1339 = 表64.get(目标701)
        if not 栈1339:
            栈1339 = 表64[' ']
        for 读取912 in range(6):
            打开793[读取912] += 栈1339[读取912] + ' '
    return 打开793

def 列66(name=None):
    return 行65(name or 写入71)
字节67 = ['▄▀█ █▀█ █▀█   ▄▀█ █▄░█ █▀▄ █▀█ █▀█ █ █▀▄', '█▀█ █▀▄ █▀▀   █▀█ █░▀█ █▀▄ █▀▄ █▄█ █ █▀▄']
文本68 = ('7b22617070223a2241525058222c2276', '657273696f6e223a2235352e30222c22', '636f64656e616d65223a22474154454b', '4545504552222c22617574686f72223a', '2241686d616564646576222c22636861', '6e6e656c223a22742e6d652f41686d61', '65645f64657631222c227365616c223a', '22316366636334636630353936323964', '64643963653332373666333635393733', '64653633393764346430623830396333', '65653636646665323437396466376166', '36227d')

def 名字69():
    try:
        表744 = bytes.fromhex(''.join(文本68)).decode('utf-8')
        return json.loads(表744)
    except Exception:
        return {'app': '?', 'version': '?', 'codename': '?', 'author': '?', 'channel': '?', 'seal': ''}
检查70 = 名字69()
写入71 = 检查70.get('app', '?')
读取72 = 检查70.get('version', '?')
打开73 = 检查70.get('codename', '?')
关闭74 = 检查70.get('author', '?')
构建75 = 检查70.get('channel', '?')
解析76 = f'ANDROID REVERSE ENGINEERING  ·  v{读取72} {打开73}'
扫描77 = 'REVERSE ENGINEERING · DECOMPILE · UNPACK · PATCH · SIGN'
修补78 = f'{关闭74}  ·  {构建75}'
报告79 = {'big': True}

def 变量80():
    列946 = min(72, 缓存3.clamp(46, 78))
    键703 = 栈59('ARPXTOOL', 行25, True)
    列表847 = ['']
    检查950 = re.sub('^v?\\d+(\\.\\d+)*\\s*', '', 数据88(解析76).split('·')[-1].strip()).upper()
    列表847.append('  ' + 键703 + '   ' + 索引4(栈19)('v%s' % 读取72) + (索引4(源20)('   ' + 检查950) if 检查950 else ''))
    列表847.append('  ' + 索引4(源20)(节点57(数据88(扫描77), 列946 - 6)))
    列表847.append('  ' + 索引4(栈19)(节点57(数据88(修补78), 列946 - 6)))
    列表847.append('')
    return 值62(列表847, [标记10, 队列11, 映射12], width=列946)
参数81 = {'on': False, 'file': None, 'count': 0}

def 结果82(表704, 行705='step'):
    if not 参数81['on']:
        return
    参数81['count'] += 1
    解析796 = time.strftime('%H:%M:%S')
    计数885 = '%s  %-6s %s' % (解析796, 行705, 表704)
    if 参数81['file']:
        try:
            with open(参数81['file'], 'a', encoding='utf-8') as 构建915:
                构建915.write(计数885 + '\n')
        except Exception:
            pass
    if 缓存3.enabled:
        sys.stdout.write('\r' + 索引4.CLR)
    print('  ' + 索引4(映射12)('~') + ' ' + 打开33(节点57(计数885, 缓存3.clamp(50, 110))))
缓存83 = {'on': False}

def 索引84(列706):
    结果82(' '.join((str(队列691) for 队列691 in 列706)), 'exec')

def 计数85(列706, 字节707, 文本708, 名字709, 检查710):
    if not 缓存83['on']:
        return
    if 缓存3.enabled:
        sys.stdout.write('\r' + 索引4.CLR)
    print('  ' + 索引4(映射12)('$') + ' ' + 修补38(节点57(' '.join((str(队列691) for 队列691 in 列706)), 缓存3.clamp(40, 110))))
    ok = 字节707 == 0
    print('    ' + (关闭34(数据48) if ok else 索引4(键23, True)(状态49)) + ' ' + 打开33('exit %s · %.1fs · %d line(s) out · %d line(s) err' % (字节707, 检查710, len((文本708 or '').splitlines()), len((名字709 or '').splitlines()))))
    for 修补718, 表744 in (('out', 文本708), ('err', 名字709)):
        值702 = [目标1421 for 目标1421 in (表744 or '').splitlines() if 目标1421.strip()]
        if not 值702:
            continue
        for 计数885 in 值702[:6]:
            print('      ' + 打开33(节点57(计数885, 100)))
        if len(值702) > 6:
            print('      ' + 打开33('... %d more line(s)' % (len(值702) - 6)))
路径86 = ('wipe', 'typewriter', 'scan', 'decode', 'slide', 'pulse', 'glitch', 'none')
列表87 = {'style': 'wipe'}

def 数据88(条目693):
    return re.sub('\\033\\[[0-9;?]*[A-Za-z]', '', 条目693)

def 状态89(写入711, 读取712=None):
    width = max(1, max((区块55(目标1421) for 目标1421 in 写入711)))
    文本708 = []
    for 名字949 in 写入711:
        计数805 = []
        for 参数1561, 目标701 in enumerate(名字949):
            if 目标701 == ' ':
                计数805.append(' ')
                continue
            键863 = 数据8(行25, 参数1561 / max(1, width - 1))
            计数805.append(索引4(读取712(键863) if 读取712 else 键863, True)(目标701))
        文本708.append(''.join(计数805))
    return 文本708

def 标记90(写入711, 打开713):
    width = max(1, max((区块55(目标1421) for 目标1421 in 写入711)))
    for 读取952 in range(打开713 + 1):
        源1340 = int(width * min(1.0, 读取952 / max(1, 打开713 - 5)))
        变量1280 = 读取952 / max(1, 打开713) * (width + 24) - 12
        文本708 = []
        for 名字949 in 写入711:
            计数805 = []
            for 参数1561, 目标701 in enumerate(名字949):
                if 目标701 == ' ' or 参数1561 > 源1340:
                    计数805.append(' ')
                    continue
                构建1675 = max(0.0, 1.0 - abs(参数1561 - 变量1280) / 8.0)
                键863 = 数据8(行25, 参数1561 / max(1, width - 1))
                计数805.append(索引4(列表7(键863, 值22, 构建1675 * 0.9), True)(目标701))
            文本708.append(''.join(计数805))
        步骤58.paint(文本708)

def 队列91(写入711, 打开713):
    total = sum((len(目标1421) for 目标1421 in 写入711))
    打开953 = max(1, total // max(1, 打开713))
    for 读取952 in range(打开713 + 1):
        源820 = 读取952 * 打开953
        文本708 = []
        for 名字949 in 写入711:
            行865 = max(0, min(len(名字949), 源820))
            源820 -= 行865
            head = 名字949[:行865]
            列1186 = 名字949[行865:]
            文本708.append(索引4(表24, True)(head) + 打开33(列1186))
        步骤58.paint(文本708)

def 映射92(写入711, 打开713):
    width = max(1, max((区块55(目标1421) for 目标1421 in 写入711)))
    for 读取952 in range(打开713 + 1):
        变量1280 = 读取952 / max(1, 打开713) * (width + 16) - 8
        文本708 = []
        for 名字949 in 写入711:
            计数805 = []
            for 参数1561, 目标701 in enumerate(名字949):
                if 目标701 == ' ':
                    计数805.append(' ')
                    continue
                构建1675 = max(0.0, 1.0 - abs(参数1561 - 变量1280) / 5.0)
                键863 = 数据8(行25, 参数1561 / max(1, width - 1))
                计数805.append(索引4(列表7(键863, 值22, 构建1675), True)(目标701))
            文本708.append(''.join(计数805))
        步骤58.paint(文本708)

def 条目93(写入711, 打开713):
    关闭954 = '01<>/\\|_-=+*#%$@'
    width = max(1, max((区块55(目标1421) for 目标1421 in 写入711)))
    for 读取952 in range(打开713 + 1):
        目标1341 = 读取952 / max(1, 打开713)
        文本708 = []
        for 名字949 in 写入711:
            计数805 = []
            for 参数1561, 目标701 in enumerate(名字949):
                if 目标701 == ' ':
                    计数805.append(' ')
                    continue
                解析1676 = 参数1561 / max(1, width - 1)
                if 解析1676 < 目标1341:
                    计数805.append(索引4(数据8(行25, 解析1676), True)(目标701))
                else:
                    名字909 = random.Random(读取952 * 7919 + 参数1561 * 131)
                    计数805.append(打开33(名字909.choice(关闭954)))
            文本708.append(''.join(计数805))
        步骤58.paint(文本708)

def 偏移94(写入711, 打开713):
    for 读取952 in range(打开713 + 1):
        值1342 = int((1 - min(1.0, 读取952 / max(1, 打开713))) * 24)
        文本708 = []
        for 名字949 in 写入711:
            文本708.append(' ' * 值1342 + 索引4(数据8(行25, 0.5), True)(名字949) if 值1342 == 0 else ' ' * 值1342 + 打开33(名字949))
        步骤58.paint(文本708)

def 区块95(写入711, 打开713):
    for 读取952 in range(打开713 + 1):
        level = 0.5 + 0.5 * math.sin(读取952 / max(1, 打开713) * math.pi * 2)
        文本708 = []
        for 名字949 in 写入711:
            文本708.append(''.join((' ' if 目标701 == ' ' else 索引4(列表7(数据8(行25, 0.5), 值22, level * 0.7), True)(目标701) for 目标701 in 名字949)))
        步骤58.paint(文本708)

def 句柄96(写入711, 打开713):
    width = max(1, max((区块55(目标1421) for 目标1421 in 写入711)))
    for 读取952 in range(打开713 + 1):
        键1343 = 读取952 >= 打开713 - 3
        文本708 = []
        for 名字949 in 写入711:
            if 键1343:
                文本708.append(''.join((' ' if 目标701 == ' ' else 索引4(数据8(行25, 读取912 / max(1, width - 1)), True)(目标701) for 读取912, 目标701 in enumerate(名字949))))
                continue
            名字909 = random.Random(读取952 * 104729 + len(名字949))
            计数805 = []
            for 目标701 in 名字949:
                if 目标701 == ' ':
                    计数805.append(' ')
                elif 名字909.random() < 0.18:
                    计数805.append(索引4(名字909.choice([键23, 标记10, 映射12]))(名字909.choice('▚▞░▒')))
                else:
                    计数805.append(索引4(数据8(行25, 0.4), True)(目标701))
            文本708.append(''.join(计数805))
        步骤58.paint(文本708)

def 节点97(关闭714=False):
    值702 = 变量80()
    构建955 = 列表87['style']
    if 关闭714 or not 缓存3.enabled or 构建955 == 'none':
        for 名字949 in 值702:
            print(名字949)
        return
    写入711 = [数据88(目标1421) for 目标1421 in 值702]
    打开713 = 22
    sys.stdout.write(索引4.HIDE)
    try:
        表1344 = {'wipe': 标记90, 'typewriter': 队列91, 'scan': 映射92, 'decode': 条目93, 'slide': 偏移94, 'pulse': 区块95, 'glitch': 句柄96}.get(构建955, 标记90)
        表1344(写入711, 打开713)
        步骤58.paint(状态89(写入711))
    finally:
        sys.stdout.write(索引4.SHOW)
        步骤58.close()

def 步骤98(表704, 构建715=0.55, 句柄696=None):
    句柄696 = 句柄696 or 列26
    if not 缓存3.enabled:
        return
    text = f'  {表704}'
    width = 区块55(text)
    end = time.time() + 构建715
    sys.stdout.write(索引4.HIDE)
    try:
        while time.time() < end:
            条目693 = 1.0 - (end - time.time()) / 构建715
            变量1280 = 条目693 * (width + 14) - 7
            计数805 = []
            for 读取912, 目标701 in enumerate(text):
                if 目标701 == ' ':
                    计数805.append(目标701)
                    continue
                行785 = abs(读取912 - 变量1280)
                构建1675 = max(0.0, 1.0 - 行785 / 7.0)
                计数805.append(索引4(列表7(数据8(句柄696, 读取912 / max(1, width - 1)), 值22, 构建1675))(目标701))
            sys.stdout.write('\r' + ''.join(计数805) + 索引4.CLR)
            sys.stdout.flush()
            time.sleep(0.018)
    finally:
        sys.stdout.write('\r' + 索引4.CLR)
        sys.stdout.write(索引4.SHOW)
        sys.stdout.flush()

def 栈99(text, 解析716=0.006, 扫描717='  '):
    if not 缓存3.enabled or 解析716 <= 0:
        print(扫描717 + text)
        return
    sys.stdout.write(索引4.HIDE + 扫描717)
    for 目标701 in text:
        sys.stdout.write(目标701)
        sys.stdout.flush()
        time.sleep(解析716)
    sys.stdout.write(索引4.SHOW + '\n')
    sys.stdout.flush()

def 源100(构建715=0.7):
    if not 缓存3.enabled:
        return
    width = 缓存3.clamp(24, 60)
    end = time.time() + 构建715
    sys.stdout.write(索引4.HIDE)
    try:
        while time.time() < end:
            条目693 = time.time() * 6
            源1380 = []
            for 报告1079 in range(width):
                解析956 = (math.sin(报告1079 / 4.0 + 条目693) + 1) / 2
                检查910 = '▁▂▃▄▅▆▇█'[min(7, int(解析956 * 7.99))]
                源1380.append(索引4(数据8(列26, 解析956), True)(检查910))
            sys.stdout.write('\r  ' + ''.join(源1380) + 索引4.CLR)
            sys.stdout.flush()
            time.sleep(0.03)
    finally:
        sys.stdout.write('\r' + ' ' * 缓存3.width + '\r' + 索引4.SHOW)
        sys.stdout.flush()

def 目标101(修补718, 报告719, 解析716=0.035, 句柄696=None):
    句柄696 = 句柄696 or 文本28
    步骤698 = len(报告719)
    if not 缓存3.enabled:
        for 节点697 in 报告719:
            print(f'  {数据48} {节点697}')
        return
    width = 缓存3.clamp(18, 34)
    sys.stdout.write(索引4.HIDE)
    try:
        for 读取912, 打开953 in enumerate(报告719):
            for 条目1013 in range(4):
                句柄1336 = (读取912 + 条目1013 / 4) / 步骤698
                节点1337 = 句柄1336 * width
                句柄1256 = int(节点1337)
                列表847 = '█' * 句柄1256 + (结果42[int((节点1337 - 句柄1256) * 8)] if 句柄1256 < width else '') + '░' * max(0, width - 句柄1256 - 1)
                扫描1677 = 参数41[(读取912 * 4 + 条目1013) % len(参数41)]
                写入791 = 数据8(句柄696, 句柄1336)
                sys.stdout.write('\r  ' + 索引4(写入791)(扫描1677) + ' ' + 栈59(列表847, 句柄696))
                sys.stdout.write(' ' + 索引4(表24)(节点57(打开953, 34).ljust(34)) + 索引4.CLR)
                sys.stdout.flush()
                time.sleep(解析716 / 4)
            print()
    finally:
        sys.stdout.write(索引4.SHOW)
        sys.stdout.flush()

def 值102(变量720):
    解析956 = hashlib.sha256()
    with open(变量720, 'rb') as 读取952:
        for 行1345 in iter(lambda: 读取952.read(1 << 20), b''):
            解析956.update(行1345)
    return 解析956.hexdigest()

def 键103(参数721):
    return hashlib.sha256(参数721).hexdigest()

def 表104(步骤698):
    for 目标861 in ('B', 'KB', 'MB', 'GB'):
        if 步骤698 < 1024 or 目标861 == 'GB':
            return f'{步骤698:.0f} {目标861}' if 目标861 == 'B' else f'{步骤698:.1f} {目标861}'
        步骤698 /= 1024.0
    return f'{步骤698:.1f} GB'

def 行105(变量720, 参数721, mode='wb'):
    变量720 = Path(变量720)
    变量720.parent.mkdir(parents=True, exist_ok=True)
    扫描797 = 变量720.with_suffix(变量720.suffix + '.arptmp')
    with open(扫描797, mode) as 读取952:
        读取952.write(参数721)
        读取952.flush()
        os.fsync(读取952.fileno())
    os.replace(扫描797, 变量720)

def 列106(name):
    return re.sub('[^A-Za-z0-9._-]', '_', os.path.basename(name))

def 字节107(结果722):
    return shutil.which(结果722)

def 文本108():
    return 字节107('java') is not None

def 名字109(变量720):
    try:
        return shutil.disk_usage(变量720).free
    except Exception:
        return 0

def 检查110(列706, cwd=None, timeout=3000, env=None):
    索引84(列706)
    扫描957 = time.time()
    try:
        值1062 = subprocess.run(列706, cwd=cwd, timeout=timeout, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, errors='replace')
        字节707, 文本708, 名字709 = (值1062.returncode, 值1062.stdout, 值1062.stderr)
    except subprocess.TimeoutExpired:
        字节707, 文本708, 名字709 = (-9, '', 'timeout')
    except FileNotFoundError:
        字节707, 文本708, 名字709 = (-2, '', 'not found')
    except Exception as 修补958:
        字节707, 文本708, 名字709 = (-1, '', str(修补958))
    计数85(列706, 字节707, 文本708, 名字709, time.time() - 扫描957)
    return (字节707, 文本708, 名字709)
写入111 = re.compile('(error|exception|failed|fatal|warn|I: Using|I: Baksmaling|I: Smaling|I: Building|I: Built|Signed|Verif|success|complete)', re.I)
读取112 = {'show_command': True}

def 打开113(列706):
    变量760 = []
    for 队列691 in 列706:
        队列691 = str(队列691)
        if len(队列691) > 48:
            队列691 = 队列691[:22] + '...' + 队列691[-22:]
        变量760.append(队列691 if ' ' not in 队列691 else "'" + 队列691 + "'")
    return ' '.join(变量760)

def 关闭114(列706, 修补718, cwd=None, timeout=3000, env=None, 缓存723=False, 索引724=None):
    索引84(列706)
    start = time.time()
    if 缓存3.enabled and (not 缓存723) and 读取112['show_command']:
        print('  ' + 打开33('$ ') + 打开33(节点57(打开113(列706), 缓存3.clamp(40, 104))))
    try:
        列1346 = subprocess.Popen(列706, cwd=cwd, env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1, errors='replace')
    except FileNotFoundError:
        键63.bad(修补718 + ': executable not found')
        return (-2, [])
    except Exception as 修补958:
        键63.bad('%s: %s' % (修补718, 修补958))
        return (-1, [])
    列866 = 0
    errors = []
    报告959 = 0
    变量960 = ''
    参数961 = 列1346.stdout
    if 缓存3.enabled:
        sys.stdout.write(索引4.HIDE)
    try:
        while True:
            计数885 = 参数961.readline()
            if not 计数885:
                break
            列866 += 1
            报告1039 = 计数885.rstrip('\n').strip()
            if not 报告1039:
                continue
            关闭1074 = 报告1039.lower()
            if 索引724 is not None:
                索引724.append(报告1039)
            if 'error' in 关闭1074 or 'exception' in 关闭1074 or 'failed' in 关闭1074 or ('fatal' in 关闭1074):
                errors.append(节点57(报告1039, 140))
            if 缓存3.enabled and (not 缓存723) and 写入111.search(报告1039) and (报告1039 != 变量960) and (len(报告1039) < 140):
                变量960 = 报告1039
                sys.stdout.write('\r' + 索引4.CLR)
                print('    ' + 打开33('|') + ' ' + 索引4(栈19)(节点57(报告1039, 104)))
            elif 缓存3.enabled:
                报告959 += 1
                检查710 = int(time.time() - start)
                sys.stdout.write('\r' + 索引4.CLR + '  ' + 索引4(数据8(列26, 0.4))(参数41[报告959 % len(参数41)]) + ' ' + 索引4(表24)(修补718) + ' ' + 索引4(源20)('%d lines - %ds' % (列866, 检查710)))
                sys.stdout.flush()
            if time.time() - start > timeout:
                列1346.kill()
                errors.append('timeout')
                break
        列1346.wait()
    except KeyboardInterrupt:
        列1346.kill()
        raise
    finally:
        if 缓存3.enabled:
            sys.stdout.write(索引4.SHOW)
    检查710 = time.time() - start
    if 缓存83['on']:
        计数85(列706, 列1346.returncode, '\n'.join(errors[-6:]), '', 检查710)
    if 缓存3.enabled:
        sys.stdout.write('\r' + 索引4.CLR)
    if 列1346.returncode == 0:
        print('  ' + 关闭34(数据48) + ' ' + 修补38(修补718) + ' ' + 打开33('- %d lines - %.1fs' % (列866, 检查710)))
    else:
        print('  ' + 解析36(状态49) + ' ' + 修补38('%s exit %d' % (修补718, 列1346.returncode)) + ' ' + 打开33('- %.1fs' % 检查710))
        for 修补958 in errors[:3]:
            print('    ' + 索引4(键23)(节点57(修补958, 120)))
    return (列1346.returncode, errors)
构建115 = {3: 'x86', 62: 'x86_64', 40: 'arm', 183: 'aarch64', 243: 'riscv'}

def 解析116(参数721):
    if len(参数721) < 52 or 参数721[:4] != b'\x7fELF':
        return None
    cls = 参数721[4]
    结果962 = '<' if 参数721[5] == 1 else '>'
    try:
        字节1347 = struct.unpack_from(结果962 + 'H', 参数721, 18)[0]
        计数965 = 64 if cls == 2 else 32
    except Exception:
        return None
    return {'bits': 计数965, 'machine': 字节1347, 'arch': 构建115.get(字节1347, 'unknown'), 'endian': 结果962}
扫描117 = {'arm64-v8a': ('aarch64', 64), 'armeabi-v7a': ('arm', 32), 'armeabi': ('arm', 32), 'x86': ('x86', 32), 'x86_64': ('x86_64', 64), 'riscv64': ('riscv', 64)}
修补118 = re.compile('^[0-9A-Fa-f.??]{2}$')

def 报告119(计数725):
    缓存963 = 计数725.split()
    变量760 = []
    for 索引964 in 缓存963:
        if not 修补118.match(索引964):
            return None
        列906, 行905 = (索引964[0].upper(), 索引964[1].upper())
        if 列906 in '.?' and 行905 in '.?':
            变量760.append(b'.')
        elif 列906 in '.?':
            步骤818 = int(行905, 16)
            修补1678 = bytes([解析956 << 4 | 步骤818 for 解析956 in range(16)])
            变量760.append(b'[' + b''.join((re.escape(bytes([报告1079])) for 报告1079 in 修补1678)) + b']')
        elif 行905 in '.?':
            步骤818 = int(列906, 16) << 4
            变量760.append(b'[' + re.escape(bytes([步骤818])) + b'-' + re.escape(bytes([步骤818 + 15])) + b']')
        else:
            变量760.append(re.escape(bytes([int(索引964, 16)])))
    if not 变量760:
        return None
    return re.compile(b''.join(变量760), re.S)
变量120 = {'aarch64': bytes.fromhex('200080d2c0035fd6'), 'arm': bytes.fromhex('01207047'), 'x86': bytes.fromhex('b801000000c3'), 'x86_64': bytes.fromhex('b801000000c3'), 'riscv': bytes.fromhex('1305100067800000')}
参数121 = {'aarch64': ['F. 0F 1C F8 F. 5. 01 A9 F. 5. 02 A9 F. .. 03 A9 .. .. .. .. 68 1A 40 F9', 'F. 43 01 D1 FE 67 01 A9 F8 5F 02 A9 F6 57 03 A9 F4 4F 04 A9 13 00 40 F9 F4 03 00 AA 68 1A 40 F9', 'FF 43 01 D1 FE 67 01 A9 ?? ?? 06 94 ?? 7? 06 94 68 1A 40 F9 15 15 41 F9 B5 00 00 B4 B6 4A 40 F9', 'FF .3 01 D1 F. .. 01 A9 .. .. .. 94 .. .. .. 52 48 00 00 39 1A 50 40 F9 DA 02 00 B4 48 03 40 F9'], 'arm': ['2D E9 F. 4. D0 F8 00 80 81 46 D8 F8 18 00 D0 F8'], 'x86': ['55 89 E5 53 57 56 83 E4 F0 83 EC 20 E8 00 00 00 00 5B 81 C3 2B 79 66 00 8B 7D 08 8B 17 8B 42 18 8B 80 88 01'], 'x86_64': ['55 41 57 41 56 41 55 41 54 53 50 49 89 F. 4. 8B .. 4. 8B 4. 30 4C 8B .. .. 0. 00 00 4D 85 .. 74 1. 4D 8B', '55 41 57 41 56 41 55 41 54 53 48 83 EC 18 49 89 FF 48 8B 1F 48 8B 43 30 4C 8B A0 28 02 00 00 4D 85 E4 74', '55 41 57 41 56 41 55 41 54 53 48 83 EC 18 49 89 FE 4C 8B 27 49 8B 44 24 30 48 8B 98 D0 01 00 00 48 85 DB']}
结果122 = {'aarch64': ['F. 0F 1C F8 F. .. 0. .. .. .. .. .9 .. .. 0. .. 68 1A 40 F9 15 .. 4. F9 B5 00 00 B4 B6 46 40 F9', 'FF 03 05 D1 FC 6B 0F A9 F9 63 10 A9 F7 5B 11 A9 F5 53 12 A9 F3 7B 13 A9 08 0A 80 52 48 00 00 39 16 54 40 F9 56 07 00 B4 C8 02 40 F9 08 07 00 B4 29 20 40 A9 F3 03 02 AA', 'FF 83 01 D1 FA 67 01 A9 F8 5F 02 A9 F6 57 03 A9 F4 4F 04 A9 FD 7B 05 A9 FD 43 01 91 F. 03 00 AA .. 0? 40 F9 ?8 1? 40 F9 15 ?? 4? F9 B5 00 00 B4'], 'arm': ['2D E9 F0 4F A3 B0 81 46 50 20 10 70 D9 F8 98 70 00 2F', '2D E9 F0 4F A3 B0 82 46 50 20 10 70'], 'x86': [], 'x86_64': ['55 41 57 41 56 41 55 41 54 53 50 49 89 FE 48 8B 1F 48 8B 43 30 4C 8B B8 D0 01 00 00 4D 85 FF 74 12 4D 8B A7 90 00 00 00 4D 85 E4 74 4A 49 8B 04 24 EB 46', '55 41 57 41 56 41 55 41 54 53 48 83 EC 38 C6 02 50 48 8B AF A. 00 00 00 48 85 ED 74 7. 48 83 7D 00 00 74', '55 41 57 41 56 41 55 41 54 53 48 81 EC F8 00 00 00 C6 02 50 48 8B 9F A8 00 00 00 48 85 DB']}
缓存123 = {}
索引124 = 'ssl_verify_peer_cert'
计数125 = 'ssl_crypto_x509_session_verify_cert_chain'
路径126 = {'FF .3 01 D1 F. .. 01 A9 .. .. .. 94 .. .. .. 52 48 00 00 39 1A 50 40 F9 DA 02 00 B4 48 03 40 F9': (1, 计数125), 'FF 03 05 D1 FC 6B 0F A9 F9 63 10 A9 F7 5B 11 A9 F5 53 12 A9 F3 7B 13 A9 08 0A 80 52 48 00 00 39 16 54 40 F9 56 07 00 B4 C8 02 40 F9 08 07 00 B4 29 20 40 A9 F3 03 02 AA': (1, 计数125)}

def 列表127(计数725):
    return 路径126.get(计数725, (0, 索引124))

def 数据128(路径726, 列表727=False):
    key = (路径726, bool(列表727))
    if key not in 缓存123:
        偏移974 = 结果122 if 列表727 else 参数121
        文本708 = []
        for 值1062 in 偏移974.get(路径726, []):
            映射1132 = 报告119(值1062)
            if 映射1132:
                ret, name = 列表127(值1062)
                文本708.append((映射1132, ret, name))
        缓存123[key] = 文本708
    return 缓存123[key]

def 状态129(路径726, ret):
    ret = 1 if ret else 0
    if 路径726 == 'aarch64':
        return struct.pack('<II', 3531603968 | ret << 5, 3596551104)
    if 路径726 == 'arm':
        return struct.pack('<HH', 8192 | ret, 18288)
    if 路径726 in ('x86', 'x86_64'):
        return bytes((184, ret, 0, 0, 0, 195))
    if 路径726 == 'riscv':
        return 变量120.get('riscv')
    return None

class 标记130:

    def __init__(self, 变量720, 路径726):
        self.path = 变量720
        self.arch = 路径726
        self.hits = []
        self.already = 0
        self.error = None
        self.elf = None
        self.names = []

def 队列131(变量720, 数据728):
    try:
        参数721 = Path(变量720).read_bytes()
    except Exception:
        return {}
    if len(参数721) < 52 or 参数721[:4] != b'\x7fELF':
        return {}
    计数965 = 64 if 参数721[4] == 2 else 32
    end = '<' if 参数721[5] == 1 else '>'
    try:
        if 计数965 == 64:
            结果1562 = struct.unpack_from(end + 'Q', 参数721, 32)[0]
            缓存1563 = struct.unpack_from(end + 'Q', 参数721, 40)[0]
            索引1564 = struct.unpack_from(end + 'H', 参数721, 54)[0]
            计数1565 = struct.unpack_from(end + 'H', 参数721, 56)[0]
            路径1566 = struct.unpack_from(end + 'H', 参数721, 58)[0]
            列表1567 = struct.unpack_from(end + 'H', 参数721, 60)[0]
        else:
            结果1562 = struct.unpack_from(end + 'I', 参数721, 28)[0]
            缓存1563 = struct.unpack_from(end + 'I', 参数721, 32)[0]
            索引1564 = struct.unpack_from(end + 'H', 参数721, 42)[0]
            计数1565 = struct.unpack_from(end + 'H', 参数721, 44)[0]
            路径1566 = struct.unpack_from(end + 'H', 参数721, 46)[0]
            列表1567 = struct.unpack_from(end + 'H', 参数721, 48)[0]
    except Exception:
        return {}
    if not 缓存1563 or not 列表1567 or 列表1567 > 4096:
        return {}
    路径966 = []
    for 读取912 in range(min(计数1565, 256)):
        映射692 = 结果1562 + 读取912 * 索引1564
        try:
            数据1568 = struct.unpack_from(end + 'I', 参数721, 映射692)[0]
            if 计数965 == 64:
                键1503 = struct.unpack_from(end + 'Q', 参数721, 映射692 + 8)[0]
                值1502 = struct.unpack_from(end + 'Q', 参数721, 映射692 + 16)[0]
                表1504 = struct.unpack_from(end + 'Q', 参数721, 映射692 + 32)[0]
            else:
                键1503 = struct.unpack_from(end + 'I', 参数721, 映射692 + 4)[0]
                值1502 = struct.unpack_from(end + 'I', 参数721, 映射692 + 8)[0]
                表1504 = struct.unpack_from(end + 'I', 参数721, 映射692 + 16)[0]
        except Exception:
            continue
        if 数据1568 == 1:
            路径966.append((值1502, 键1503, 表1504))

    def to_off(步骤818):
        for 状态1569, 行745, 标记1570 in 路径966:
            if 状态1569 <= 步骤818 < 状态1569 + 标记1570:
                return 行745 + (步骤818 - 状态1569)
        return None
    want = set(数据728)
    文本708 = {}
    列表967 = 'Q' if 计数965 == 64 else 'I'
    for 读取912 in range(列表1567):
        映射692 = 缓存1563 + 读取912 * 路径1566
        try:
            队列1571 = struct.unpack_from(end + 'I', 参数721, 映射692 + 4)[0]
            if 计数965 == 64:
                报告1679 = struct.unpack_from(end + 'Q', 参数721, 映射692 + 24)[0]
                变量1680 = struct.unpack_from(end + 'Q', 参数721, 映射692 + 32)[0]
                参数1681 = struct.unpack_from(end + 'I', 参数721, 映射692 + 40)[0]
                结果1682 = struct.unpack_from(end + 'Q', 参数721, 映射692 + 56)[0]
            else:
                报告1679 = struct.unpack_from(end + 'I', 参数721, 映射692 + 16)[0]
                变量1680 = struct.unpack_from(end + 'I', 参数721, 映射692 + 20)[0]
                参数1681 = struct.unpack_from(end + 'I', 参数721, 映射692 + 24)[0]
                结果1682 = struct.unpack_from(end + 'I', 参数721, 映射692 + 36)[0]
        except Exception:
            continue
        if 队列1571 not in (2, 11) or not 变量1680:
            continue
        try:
            映射1572 = 缓存1563 + 参数1681 * 路径1566
            if 计数965 == 64:
                缓存1683 = struct.unpack_from(end + 'Q', 参数721, 映射1572 + 24)[0]
            else:
                缓存1683 = struct.unpack_from(end + 'I', 参数721, 映射1572 + 16)[0]
        except Exception:
            continue
        计数1205 = 结果1682 or (24 if 计数965 == 64 else 16)
        for 名字989 in range(变量1680 // 计数1205):
            条目1573 = 报告1679 + 名字989 * 计数1205
            try:
                索引1684 = struct.unpack_from(end + 'I', 参数721, 条目1573)[0]
                计数1685 = struct.unpack_from(end + 列表967, 参数721, 条目1573 + (8 if 计数965 == 64 else 4))[0]
            except Exception:
                continue
            if not 索引1684 or not 计数1685:
                continue
            修补958 = 参数721.find(b'\x00', 缓存1683 + 索引1684)
            if 修补958 < 0:
                continue
            偏移1574 = 参数721[缓存1683 + 索引1684:修补958].decode('ascii', 'ignore')
            if 偏移1574 in want:
                行745 = to_off(计数1685 & ~1)
                if 行745 is not None:
                    文本708[偏移1574] = 行745
    return 文本708

def 映射132(变量720, 路径726, dry=False):
    字节827 = 标记130(变量720, 路径726)
    try:
        参数721 = Path(变量720).read_bytes()
    except Exception as 修补958:
        字节827.error = f'read: {修补958}'
        return 字节827
    info = 解析116(参数721)
    字节827.elf = info
    if info is None:
        字节827.error = 'not an ELF object'
        return 字节827
    字节827.arch = info['arch']
    状态969 = 扫描117.get(路径726)
    if 状态969 and (info['arch'] != 状态969[0] or info['bits'] != 状态969[1]):
        字节827.error = f"ABI mismatch: {info['arch']}/{info['bits']} vs {状态969[0]}/{状态969[1]}"
        return 字节827
    修补798 = {}
    for 文本1348, ret, name in 数据128(info['arch']):
        for 句柄776 in 文本1348.finditer(参数721):
            修补798.setdefault(句柄776.start(), (ret, name))
    if not 修补798:
        for 文本1348, ret, name in 数据128(info['arch'], 列表727=True):
            for 句柄776 in 文本1348.finditer(参数721):
                修补798.setdefault(句柄776.start(), (ret, name))
    if not 修补798:
        for 区块1575, 句柄1576 in 队列131(变量720, (索引124, 计数125)).items():
            修补798[句柄1576] = (1 if 区块1575 == 计数125 else 0, 区块1575 + ' (symbol)')
    if not 修补798:
        句柄816 = {}
        for 状态729 in 参数121.get(info['arch'], []) + 结果122.get(info['arch'], []):
            节点1577 = 状态729.split()
            ret, name = 列表127(状态729)
            结果1122 = 状态129(info['arch'], ret)
            if not 结果1122 or len(节点1577) <= len(结果1122):
                continue
            映射972 = 报告119(' '.join(节点1577[len(结果1122):]))
            if 映射972 is None:
                continue
            for 句柄776 in re.finditer(re.escape(结果1122) + 映射972.pattern, 参数721):
                句柄816.setdefault(句柄776.start(), (name, ret))
        for 行745 in sorted(句柄816):
            name, ret = 句柄816[行745]
            字节827.already += 1
            字节827.names.append((行745, name, ret, 'already'))
        if 字节827.already:
            return 字节827
        字节827.error = 'signature not found'
        return 字节827
    计数805 = bytearray(参数721)
    for 行745 in sorted(修补798):
        ret, name = 修补798[行745]
        结果1122 = 状态129(info['arch'], ret)
        if not 结果1122:
            字节827.error = f"no patch stub for {info['arch']}"
            return 字节827
        if 计数805[行745:行745 + len(结果1122)] == 结果1122:
            字节827.already += 1
            字节827.names.append((行745, name, ret, 'already'))
            continue
        if 行745 + len(结果1122) > len(计数805):
            continue
        计数805[行745:行745 + len(结果1122)] = 结果1122
        字节827.hits.append(行745)
        字节827.names.append((行745, name, ret, 'patched'))
    if 字节827.hits and (not dry):
        计数1165 = Path(str(变量720) + '.arpbak')
        if not 计数1165.exists():
            shutil.copy2(变量720, 计数1165)
        行105(变量720, bytes(计数805))
        check = Path(变量720).read_bytes()
        for 行745, name, ret, 路径1246 in 字节827.names:
            结果1122 = 状态129(info['arch'], ret)
            if 路径1246 == 'patched' and check[行745:行745 + len(结果1122)] != 结果1122:
                字节827.error = 'write verification failed'
                shutil.copy2(计数1165, 变量720)
                字节827.hits = []
                return 字节827
    return 字节827

def 条目133(状态729):
    字节787 = Path(状态729) / 'lib'
    if not 字节787.is_dir():
        return []
    文本708 = []
    for 标记970 in sorted(字节787.iterdir()):
        if not 标记970.is_dir():
            continue
        for 偏移1254 in sorted(标记970.glob('*.so')):
            文本708.append((标记970.name, 偏移1254))
    return 文本708
偏移134 = re.compile('^\\.method[ \\t]+([^\\r\\n]+)\\r?\\n(.*?)^\\.end method', re.M | re.S)
区块135 = ('isRooted', 'isDeviceRooted', 'isRootAvailable', 'checkRoot', 'checkRooted', 'detectRoot', 'hasRootAccess', 'checkSuExists', 'isSuperuser', 'isRootedDevice', 'isRoot', 'isJailBreak', 'isEmulator', 'isRunningOnEmulator', 'detectEmulator', 'isGenymotion', 'isBlueStacks', 'isVpnActive', 'isVpnConnected', 'detectVpn', 'isVpnUsed', 'isVpnRunning', 'checkVpn', 'isFridaDetected', 'isXposedDetected', 'isHookDetected', 'isInstrumented', 'isFridaRunning', 'isDebuggerConnected', 'isBeingDebugged', 'isDebuggable', 'isTampered', 'isProxyEnabled')
句柄136 = ('checkSignature', 'verifySignature', 'validateSignature', 'isSignatureValid', 'isSignatureCorrect', 'verifyAppSignature', 'checkAppSignature', 'isSignedCorrectly', 'checkSignatures', 'verifyIntegrity', 'checkIntegrity', 'validateAppSignature', 'isSignatureVerified', 'verifySignatures')
节点137 = ('isTampered', 'checkTampered', 'isAppTampered', 'isSignatureInvalid', 'isModified')
步骤138 = {'ssl': [('X509TrustManager', ('checkServerTrusted', 'checkClientTrusted'), 0, 'X509TrustManager'), ('HostnameVerifier', ('verify',), 1, 'HostnameVerifier'), ('OkHttp CertificatePinner', ('check',), None, 'CertificatePinner'), ('CleartextPolicy', ('isCleartextTrafficPermitted',), 1, 'NetworkSecurityPolicy'), ('SslErrorHandler', ('onReceivedSslError',), None, 'SslErrorHandler'), ('WebViewClient', ('onReceivedError',), None, 'WebViewClient'), ('Conscrypt TrustManagerImpl', ('checkTrustedRecursive', 'checkTrustAnchor'), 0, 'TrustManagerImpl'), ('OkHttp ChainCleaner', ('clean',), None, 'CertificateChainCleaner'), ('Certificate Validity', ('checkValidity',), None, 'X509Certificate'), ('Client Cert Request', ('onReceivedClientCertRequest',), None, 'ClientCertRequest'), ('Hostname Verifier Wrapper', ('verifyHostname', 'checkServerTrusted'), 0, 'HostnameVerifier'), ('Cronet Verifier', ('verifyCertificateChain', 'verifyHost'), 0, 'Cronet'), ('SSL Socket Factory', ('getAcceptedIssuers',), None, 'TrustManager')], 'detect': [(步骤698, (步骤698,), 0, None) for 步骤698 in 区块135], 'signature': [(步骤698, (步骤698,), 1, None) for 步骤698 in 句柄136] + [(步骤698, (步骤698,), 0, None) for 步骤698 in 节点137]}

def 栈139(ret, 标记730, sig):
    if ret == 'V':
        if 'SslErrorHandler' in sig:
            return '    .locals 0\n\n    invoke-virtual {p2}, Landroid/webkit/SslErrorHandler;->proceed()V\n\n    return-void\n\n'
        return '    .locals 0\n\n    return-void\n\n'
    if ret in ('Z', 'I', 'B', 'S', 'C'):
        return '    .locals 1\n\n    const/4 v0, %s\n\n    return v0\n\n' % ('0x1' if 标记730 else '0x0')
    if ret in ('J', 'D'):
        return '    .locals 2\n\n    const-wide/16 v0, 0x0\n\n    return-wide v0\n\n'
    if ret == 'F':
        return '    .locals 1\n\n    const/4 v0, 0x0\n\n    return v0\n\n'
    return '    .locals 1\n\n    const/4 v0, 0x0\n\n    return-object v0\n\n'

def 源140(sig):
    if '(' not in sig:
        return (None, None)
    读取912 = sig.index('(')
    head = sig[:读取912].split()
    if not head:
        return (None, None)
    name = head[-1]
    映射972 = sig[读取912:]
    if ')' not in 映射972:
        return (None, None)
    ret = 映射972[映射972.rindex(')') + 1:].strip()
    return (name, ret)

class 目标141:

    def __init__(self):
        self.per_group = {}
        self.files = 0
        self.paths = []

    def add(self, 修补718, 步骤698=1):
        self.per_group[修补718] = self.per_group.get(修补718, 0) + 步骤698

    def total(self):
        return sum(self.per_group.values())

def 值142(状态729, 队列731):
    条目973 = 目标141()
    偏移974 = {}
    for 检查910 in 队列731:
        for 修补718, 数据728, 标记730, 步骤1578 in 步骤138.get(检查910, []):
            for 步骤698 in 数据728:
                偏移974.setdefault(步骤698, []).append((修补718, 标记730, 步骤1578))
    if not 偏移974:
        return 条目973
    区块975 = re.compile('^\\.method[ \\t]+[^\\r\\n]*\\b(' + '|'.join(sorted(map(re.escape, 偏移974), key=len, reverse=True)) + ')\\s*\\(', re.M)
    句柄976 = [行785 for 行785 in Path(状态729).iterdir() if 行785.is_dir() and 行785.name.startswith('smali')]
    for 字节787 in 句柄976:
        for 变量720 in 字节787.rglob('*.smali'):
            try:
                text = 变量720.read_text(encoding='utf-8', errors='ignore')
            except Exception:
                continue
            if not 区块975.search(text):
                continue
            键1103 = False
            栈1579 = []
            变量960 = 0
            for 句柄776 in 偏移134.finditer(text):
                sig = 句柄776.group(1)
                列表847 = 句柄776.group(2)
                name, ret = 源140(sig)
                if not name or ret is None or name not in 偏移974:
                    continue
                读取872 = None
                for 修补718, 标记730, 步骤1578 in 偏移974[name]:
                    if 步骤1578 and 步骤1578 not in text:
                        continue
                    读取872 = (修补718, 标记730)
                    break
                if 读取872 is None:
                    continue
                if len(列表847) < 190 and 列表847.count('\n') < 8:
                    continue
                结果1122 = 栈139(ret, 读取872[1], sig)
                栈1579.append(text[变量960:句柄776.start()])
                栈1579.append('.method ' + sig + '\n' + 结果1122 + '.end method')
                变量960 = 句柄776.end()
                键1103 = True
                条目973.add(读取872[0])
            if 键1103:
                栈1579.append(text[变量960:])
                try:
                    行105(变量720, ''.join(栈1579), 'w')
                    条目973.files += 1
                    条目973.paths.append(str(变量720.relative_to(状态729)))
                except Exception:
                    pass
    return 条目973
键143 = '<?xml version="1.0" encoding="utf-8"?>\n<network-security-config>\n    <base-config cleartextTrafficPermitted="true">\n        <trust-anchors>\n            <certificates src="system" />\n            <certificates src="user" />\n        </trust-anchors>\n    </base-config>\n    <debug-overrides cleartextTrafficPermitted="true">\n        <trust-anchors>\n            <certificates src="system" />\n            <certificates src="user" />\n        </trust-anchors>\n    </debug-overrides>\n</network-security-config>\n'

def 表144(状态729, 映射732, 条目733, 标记730):
    句柄776 = re.search('<' + re.escape(映射732) + '\\b[^>]*>', 状态729, re.S)
    if not 句柄776:
        return (状态729, False)
    节点977 = 句柄776.group(0)
    key = 条目733.split('=')[0]
    if re.search('[\\s]' + re.escape(key) + '\\s*=', 节点977):
        return (状态729, False)
    if 节点977.endswith('/>'):
        目标901 = 节点977[:-2].rstrip() + ' %s="%s"/>' % (条目733, 标记730)
    else:
        目标901 = 节点977[:-1].rstrip() + ' %s="%s">' % (条目733, 标记730)
    return (状态729[:句柄776.start()] + 目标901 + 状态729[句柄776.end():], True)

def 行145(状态729, 映射732, 偏移734):
    句柄776 = re.search('<' + re.escape(映射732) + '\\b[^>]*>', 状态729, re.S)
    if not 句柄776:
        return (状态729, 0)
    节点977 = 句柄776.group(0)
    目标901 = 节点977
    步骤978 = 0
    for 队列691 in 偏移734:
        名字1349 = '\\s' + re.escape(队列691) + '\\s*=\\s*"[^"]*"'
        检查1350 = re.sub(名字1349, '', 目标901)
        if 检查1350 != 目标901:
            步骤978 += 1
            目标901 = 检查1350
    return (状态729[:句柄776.start()] + 目标901 + 状态729[句柄776.end():], 步骤978)

def 列146(状态729, 区块735=True):
    索引884 = Path(状态729) / 'AndroidManifest.xml'
    if not 索引884.exists():
        return (0, [])
    text = 索引884.read_text(encoding='utf-8', errors='ignore')
    键783 = text
    栈979 = []
    for 映射732, 条目733, 标记730, 修补718 in [('application', 'android:debuggable', 'true', 'debuggable'), ('application', 'android:usesCleartextTraffic', 'true', 'cleartext'), ('application', 'android:extractNativeLibs', 'true', 'extractNativeLibs'), ('application', 'android:networkSecurityConfig', '@xml/network_security_config', 'networkSecurityConfig')]:
        text, 句柄1456 = 表144(text, 映射732, 条目733, 标记730)
        if 句柄1456:
            栈979.append(修补718)
    text, 步骤698 = 行145(text, 'application', ['android:testOnly'])
    if 步骤698:
        栈979.append('testOnly')
    if 区块735:
        text, 步骤698 = 行145(text, 'application', ['android:splitTypes', 'android:requiredSplitTypes', 'android:isolatedSplits'])
        text, 源1580 = 行145(text, 'manifest', ['android:splitTypes', 'android:requiredSplitTypes', 'android:isolatedSplits'])
        if 步骤698 or 源1580:
            栈979.append('splitTypes')
        text = re.sub('\\s*<meta-data[^>]*android:name="com\\.android\\.(vending\\.|stamp\\.|dynamic\\.apk\\.)[^"]*"[^>]*/>', '', text)
    if 'android.permission.INTERNET' not in text and '<uses-permission' not in text:
        text = text.replace('</manifest>', '    <uses-permission android:name="android.permission.INTERNET" />\n</manifest>')
        栈979.append('internet')
    if text != 键783:
        行105(索引884, text, 'w')
    return (len(栈979), 栈979)
字节147 = {'open': ('true', True), 'user': ('true', True), 'system': ('true', False), 'strict': ('false', False)}

def 文本148(状态729, 句柄736=None, mode='user'):
    源980 = Path(状态729) / 'res' / 'xml'
    源980.mkdir(parents=True, exist_ok=True)
    关闭794 = 源980 / 'network_security_config.xml'
    步骤738, 栈739 = 字节147.get(mode, 字节147['user'])
    目标981 = 键143
    if not 栈739:
        目标981 = 目标981.replace('            <certificates src="user" />\n', '')
    目标981 = 目标981.replace('cleartextTrafficPermitted="true"', 'cleartextTrafficPermitted="%s"' % 步骤738)
    if 句柄736:
        try:
            索引1244 = Path(句柄736).expanduser().read_bytes()
            字节747 = Path(状态729) / 'res' / 'raw'
            字节747.mkdir(parents=True, exist_ok=True)
            行105(字节747 / 'arp_ca.pem', 索引1244)
            目标1581 = '<certificates src="user" />' if 栈739 else '<certificates src="system" />'
            目标981 = 目标981.replace(目标1581, 目标1581 + '\n            <certificates src="@raw/arp_ca" />')
            键63.ok('embedded certificate · res/raw/arp_ca.pem')
        except Exception as 修补958:
            键63.warn('certificate embed failed · ' + 节点57(str(修补958), 60))
    行105(关闭794, 目标981, 'w')
    return True

def 名字149(节点737):
    值982 = []

    def intern(节点697):
        if 节点697 not in 值982:
            值982.append(节点697)
        return 值982.index(节点697)
    列表847 = bytearray()
    键983 = []
    for 行705, 映射732, 偏移734 in 节点737:
        if 行705 == 'start':
            参数761 = b''
            for name, 参数921, 标记730 in 偏移734:
                参数721 = intern(标记730) if 参数921 == 3 else 标记730
                参数761 += struct.pack('<IIIHBBI', 4294967295, intern(name), 4294967295, 8, 0, 参数921, 参数721 & 4294967295)
            区块1015 = struct.pack('<IIHHHHHH', 4294967295, intern(映射732), 20, 20, len(偏移734), 0, 0, 0)
            列表847 += struct.pack('<HHIII', 258, 16, 16 + len(区块1015) + len(参数761), 1, 4294967295)
            列表847 += 区块1015 + 参数761
            键983.append(映射732)
        else:
            if not 键983:
                continue
            键983.pop()
            列表847 += struct.pack('<HHIIIII', 259, 16, 24, 1, 4294967295, 4294967295, intern(映射732))
    表984 = 栈659(值982)
    return struct.pack('<HHI', 3, 8, 8 + len(表984) + len(列表847)) + 表984 + bytes(列表847)

def 检查150(步骤738=True, 栈739=True, 源740=True):

    def 句柄1296():
        文本708 = [('start', 'trust-anchors', []), ('start', 'certificates', [('src', 3, 'system')]), ('end', 'certificates', [])]
        if 栈739:
            文本708 += [('start', 'certificates', [('src', 3, 'user')]), ('end', 'certificates', [])]
        文本708.append(('end', 'trust-anchors', []))
        return 文本708
    行985 = 4294967295 if 步骤738 else 0
    节点737 = [('start', 'network-security-config', []), ('start', 'base-config', [('cleartextTrafficPermitted', 18, 行985)])]
    节点737 += 句柄1296()
    节点737.append(('end', 'base-config', []))
    if 源740:
        节点737.append(('start', 'debug-overrides', [('cleartextTrafficPermitted', 18, 行985)]))
        节点737 += 句柄1296()
        节点737.append(('end', 'debug-overrides', []))
    节点737.append(('end', 'network-security-config', []))
    return 名字149(节点737)

def 写入151(参数721, 目标741, 值742):
    try:
        if len(参数721) < 16 or 区块255(参数721, 0) != 3:
            return None
        表984 = None
        行745 = 区块255(参数721, 2) or 8
        列986 = 0
        while 行745 + 8 <= len(参数721) and 列986 < 200000:
            列986 += 1
            写入1351 = 区块255(参数721, 行745)
            读取1352 = 句柄256(参数721, 行745 + 4)
            if 读取1352 < 8:
                break
            if 写入1351 == 1 and 表984 is None:
                表984 = 栈259(参数721, 行745)
            elif 写入1351 == 258 and 表984 is not None:
                键863 = 行745 + 16
                if 表984.get(句柄256(参数721, 键863 + 4)) == 目标741:
                    列866 = 区块255(参数721, 键863 + 12)
                    start = 区块255(参数721, 键863 + 8)
                    关闭914 = 区块255(参数721, 键863 + 10) or 20
                    for 读取912 in range(min(列866, 64)):
                        队列691 = 键863 + start + 读取912 * 关闭914
                        if 表984.get(句柄256(参数721, 队列691 + 4)) != 值742:
                            continue
                        字节747 = 句柄256(参数721, 队列691 + 8)
                        if 字节747 != 4294967295:
                            return 表984.get(字节747)
                        if 偏移254(参数721, 队列691 + 15) == 3:
                            return 表984.get(句柄256(参数721, 队列691 + 16))
                        return None
            行745 += 读取1352
    except Exception:
        return None
    return None

def 读取152(键743):
    try:
        with zipfile.ZipFile(str(键743)) as 键1023:
            数据728 = set(键1023.namelist())
            if 'AndroidManifest.xml' in 数据728:
                路径1686 = 写入151(键1023.read('AndroidManifest.xml'), 'application', 'networkSecurityConfig')
                if 路径1686 and 路径1686.startswith('@xml/'):
                    报告1199 = 'res/xml/%s.xml' % 路径1686.split('/', 1)[1]
                    if 报告1199 in 数据728:
                        return 报告1199
            for name in sorted((步骤698 for 步骤698 in 数据728 if 步骤698.startswith('res/xml/') and 步骤698.endswith('.xml'))):
                try:
                    if 报告279(键1023.read(name)).elements[:1] == ['network-security-config']:
                        return name
                except Exception:
                    continue
    except Exception:
        return None
    return None

def 打开153(表744):
    文本708 = []
    行745 = 区块255(表744, 2) or 8
    列986 = 0
    while 行745 + 8 <= len(表744) and 列986 < 400000:
        列986 += 1
        写入1351 = 区块255(表744, 行745)
        读取1352 = 句柄256(表744, 行745 + 4)
        if 读取1352 < 8 or 行745 + 读取1352 > len(表744):
            return None
        文本708.append((写入1351, 行745, 表744[行745:行745 + 读取1352]))
        行745 += 读取1352
    return 文本708 if 文本708 else None

def 关闭154(表744, 行745, want='src'):
    键863 = 行745 + 16
    列866 = 区块255(表744, 键863 + 12)
    start = 区块255(表744, 键863 + 8)
    关闭914 = 区块255(表744, 键863 + 10) or 20
    for 读取912 in range(min(列866, 64)):
        队列691 = 键863 + start + 读取912 * 关闭914
        if 句柄256(表744, 队列691 + 4) == want:
            参数921 = 偏移254(表744, 队列691 + 15)
            参数721 = 句柄256(表744, 队列691 + 16)
            字节747 = 句柄256(表744, 队列691 + 8)
            return ('string', 参数721) if 参数921 == 3 else ('raw', 字节747) if 字节747 != 4294967295 else ('other', 参数721)
    return (None, None)

def 构建155(表744, 列746, 列表727):
    表984 = 栈259(表744, 列746)
    区块895 = list(表984.items)
    字节987 = {}
    for name in 列表727:
        if name not in 区块895:
            区块895.append(name)
        字节987[name] = 区块895.index(name)
    return (栈659(区块895), 字节987)

def 解析156(字节747, 文本748, 标记730=True):
    文本988 = bytearray(字节747)
    键863 = 16
    列866 = 区块255(文本988, 键863 + 12)
    start = 区块255(文本988, 键863 + 8) or 20
    关闭914 = 区块255(文本988, 键863 + 10) or 20
    参数721 = 4294967295 if 标记730 else 0
    for 名字989 in range(min(列866, 64)):
        队列691 = 键863 + start + 名字989 * 关闭914
        if 句柄256(文本988, 队列691 + 4) == 文本748:
            struct.pack_into('<H', 文本988, 队列691 + 12, 8)
            struct.pack_into('<B', 文本988, 队列691 + 14, 0)
            struct.pack_into('<B', 文本988, 队列691 + 15, 18)
            struct.pack_into('<I', 文本988, 队列691 + 8, 4294967295)
            struct.pack_into('<I', 文本988, 队列691 + 16, 参数721)
            return bytes(文本988)
    文本948 = 键863 + start + 列866 * 关闭914
    列表727 = struct.pack('<IIIHBBI', 4294967295, 文本748, 4294967295, 8, 0, 18, 参数721)
    文本988 = 文本988[:文本948] + 列表727 + 文本988[文本948:]
    struct.pack_into('<H', 文本988, 键863 + 12, 列866 + 1)
    struct.pack_into('<I', 文本988, 4, len(文本988))
    return bytes(文本988)

def 扫描157(表744):
    检查990 = 打开153(表744)
    if not 检查990:
        return (None, 'not a binary xml')
    列746 = next((列786 for 条目693, 列786, 读取1112 in 检查990 if 条目693 == 1), None)
    if 列746 is None:
        return (None, 'no string pool')
    表984 = 栈259(表744, 列746)
    写入991 = [(读取912, 行745, 字节747) for 读取912, (条目693, 行745, 字节747) in enumerate(检查990) if 条目693 == 258]
    if not 写入991:
        return (None, 'no elements')

    def name_of(行745):
        return 表984.get(句柄256(表744, 行745 + 16 + 4))
    读取992 = set()
    打开993 = 0
    关闭994 = None
    构建995 = None
    解析996 = None
    扫描997 = None
    键983 = []
    for 读取912, (条目693, 行745, 字节747) in enumerate(检查990):
        if 条目693 == 258:
            偏移1574 = name_of(行745)
            键983.append(偏移1574)
            if 关闭994 is not None:
                读取992.add(读取912)
            elif 偏移1574 in ('pin-set', 'domain-config'):
                关闭994 = len(键983)
                读取992.add(读取912)
            elif 偏移1574 == 'certificates' and 构建995 is None:
                构建995 = 读取912
            elif 偏移1574 == 'base-config' and 解析996 is None:
                解析996 = 读取912
        elif 条目693 == 259:
            if 关闭994 is not None:
                读取992.add(读取912)
                if len(键983) == 关闭994:
                    关闭994 = None
            elif 键983 and 键983[-1] == 'trust-anchors' and (扫描997 is None):
                扫描997 = 读取912
            if 键983:
                键983.pop()
    if 构建995 is None:
        return (None, 'no certificates element to clone')
    打开1353, 关闭1354 = 关闭154(表744, 检查990[构建995][1])
    修补998 = 打开1353 == 'string' and 表984.get(关闭1354) == 'user'
    try:
        构建1355 = 表984.items.index('src')
    except ValueError:
        return (None, 'no src string in the pool')
    列1306, 字节987 = 构建155(表744, 列746, ['user', 'overridePins', 'cleartextTrafficPermitted'])
    报告999 = 字节987['user']
    变量1000 = 字节987['overridePins']
    参数1001 = 字节987['cleartextTrafficPermitted']
    文本708 = []
    for 读取912, (条目693, 行745, 字节747) in enumerate(检查990):
        if 条目693 == 1:
            文本708.append(列1306)
            continue
        if 读取912 in 读取992:
            continue
        if 读取912 == 解析996:
            文本708.append(解析156(字节747, 参数1001, True))
            continue
        if 读取912 == 构建995 and (not 修补998):
            文本708.append(字节747)
            文本988 = bytearray(字节747)
            键863 = 16
            列866 = 区块255(文本988, 键863 + 12)
            start = 区块255(文本988, 键863 + 8)
            关闭914 = 区块255(文本988, 键863 + 10) or 20
            for 名字989 in range(min(列866, 64)):
                队列691 = 键863 + start + 名字989 * 关闭914
                if 句柄256(文本988, 队列691 + 4) == 构建1355:
                    struct.pack_into('<B', 文本988, 队列691 + 15, 3)
                    struct.pack_into('<I', 文本988, 队列691 + 8, 4294967295)
                    struct.pack_into('<I', 文本988, 队列691 + 16, 报告999)
                    break
            文本948 = 键863 + start + 列866 * 关闭914
            列表727 = struct.pack('<IIIHBBI', 4294967295, 变量1000, 4294967295, 8, 0, 18, 4294967295)
            文本988 = 文本988[:文本948] + 列表727 + 文本988[文本948:]
            struct.pack_into('<H', 文本988, 键863 + 12, 列866 + 1)
            struct.pack_into('<I', 文本988, 4, len(文本988))
            文本708.append(bytes(文本988))
            continue
        文本708.append(字节747)
    列表847 = b''.join(文本708)
    total = 8 + len(列表847)
    return (struct.pack('<HHI', 3, 8, total) + 列表847, "kept the app's own encoding · user CA %s" % ('already trusted' if 修补998 else 'added'))

def 修补158(变量720):
    try:
        参数721 = Path(变量720).read_bytes()
    except Exception:
        return ('', '')
    结果1002 = ''
    句柄776 = re.search(b'(\\d+\\.\\d+\\.\\d+)\\s*\\(stable\\)', 参数721)
    if 句柄776:
        结果1002 = 句柄776.group(1).decode('ascii', 'ignore')
    缓存1003 = ''
    for 句柄776 in re.finditer(b'(?<![0-9a-f])[0-9a-f]{40}(?![0-9a-f])', 参数721):
        报告1199 = 句柄776.group(0).decode('ascii')
        if len(set(报告1199)) < 6:
            continue
        缓存1003 = 报告1199
        break
    return (结果1002, 缓存1003)
报告159 = 'https://raw.githubusercontent.com/Impact-I/reFlutter/main/enginehash.csv'
变量160 = 'https://github.com/Impact-I/reFlutter/releases/download/android-v2-%s/%s'
参数161 = {'armeabi-v7a': 'libflutter_arm.so', 'armeabi': 'libflutter_arm.so', 'arm64-v8a': 'libflutter_arm64.so', 'x86': 'libflutter_x86.so', 'x86_64': 'libflutter_x64.so'}
结果162 = {}

def 缓存163():
    键863 = os.environ.get('XDG_CACHE_HOME') or os.path.join(os.path.expanduser('~'), '.cache')
    行785 = Path(键863) / 'arpxtool' / 'engines'
    try:
        行785.mkdir(parents=True, exist_ok=True)
    except Exception:
        行785 = Path(tempfile.gettempdir()) / 'arpxtool-engines'
        行785.mkdir(parents=True, exist_ok=True)
    return 行785

def 索引164(名字749=False):
    global _ENGINE_MAP
    if 结果162 and (not 名字749):
        return 结果162
    变量720 = 缓存163() / 'enginehash.csv'
    索引1004 = 变量720.exists() and time.time() - 变量720.stat().st_mtime < 7 * 86400
    if 名字749 or not 索引1004:
        try:
            栈179(报告159, 变量720, 'engine table')
        except Exception:
            pass
    偏移974 = {}
    try:
        for 计数885 in 变量720.read_text(errors='ignore').splitlines():
            变量760 = [报告1079.strip() for 报告1079 in 计数885.split(',')]
            if len(变量760) < 3 or 变量760[1] in ('Engine_commit', ''):
                continue
            偏移974[变量760[1]] = 变量760[2]
    except Exception:
        pass
    结果162 = 偏移974
    return 偏移974

def 计数165(检查750, abi, allow_net=True):
    if not allow_net:
        return (None, 'network disabled')
    结果1002, 缓存1003 = 修补158(检查750)
    if not 缓存1003:
        return (None, 'engine build id not found')
    计数1005 = 索引164().get(缓存1003)
    if not 计数1005:
        return (None, "engine %s is not in reFlutter's table" % 缓存1003)
    路径1006 = 参数161.get(abi)
    if not 路径1006:
        return (None, 'no prebuilt engine for %s' % abi)
    dest = 缓存163() / ('%s_%s' % (计数1005, 路径1006))
    if not dest.exists() or dest.stat().st_size < 1024 * 1024:
        ok = 栈179(变量160 % (计数1005, 路径1006), dest, 'patched engine')
        if not ok:
            return (None, 'download failed')
    return (dest, 'reFlutter %s for engine %s' % (路径1006, 缓存1003[:12]))

def 路径166(键743, 写入751, 读取752=None, allow_net=True):
    try:
        with zipfile.ZipFile(str(键743)) as 键1023:
            数据728 = [步骤698 for 步骤698 in 键1023.namelist() if re.match('lib/[^/]+/libflutter\\.so$', 步骤698)]
            if not 数据728:
                return []
            解析1556 = {步骤698: 键1023.read(步骤698) for 步骤698 in 数据728}
    except Exception as 修补958:
        return [('<archive>', type('R', (), {'hits': [], 'already': 0, 'error': str(修补958), 'names': [], 'arch': '?'})())]
    列表1007 = Path(写入751) / 'native'
    列表1007.mkdir(parents=True, exist_ok=True)
    文本708 = []
    数据1008 = {}
    for name in 数据728:
        abi = name.split('/')[1]
        扫描797 = 列表1007 / ('%s.so' % abi)
        if 读取752 and Path(读取752).is_file():
            报告1199 = Path(读取752)
            info = 解析116(报告1199.read_bytes()[:4096] or b'')
            want = 扫描117.get(abi)
            if want and info and ((info['arch'], info['bits']) == want):
                扫描797.write_bytes(报告1199.read_bytes())
                字节827 = 标记130(str(扫描797), abi)
                字节827.hits = [0]
                字节827.names = [(0, 'prebuilt patched engine', 1, 'patched')]
                文本708.append((name, 字节827))
                数据1008[name] = 扫描797.read_bytes()
                continue
        扫描797.write_bytes(解析1556[name])
        字节827 = 映射132(扫描797, abi)
        if not 字节827.hits and (not 字节827.already):
            列表1687, note = 计数165(扫描797, abi, allow_net)
            if 列表1687:
                扫描797.write_bytes(Path(列表1687).read_bytes())
                字节827 = 标记130(str(扫描797), abi)
                字节827.hits = [0]
                字节827.names = [(0, 'prebuilt patched engine (%s)' % note, 1, 'patched')]
        文本708.append((name, 字节827))
        if 字节827.hits:
            数据1008[name] = 扫描797.read_bytes()
    if not 数据1008:
        return 文本708
    状态1009 = Path(str(键743) + '.native')
    try:
        with zipfile.ZipFile(str(键743)) as 名字1429, zipfile.ZipFile(str(状态1009), 'w', allowZip64=True) as 检查1430:
            for 区块1415 in 名字1429.infolist():
                参数721 = 数据1008.get(区块1415.filename)
                if 参数721 is None:
                    参数721 = 名字1429.read(区块1415.filename)
                状态1609 = zipfile.ZipInfo(区块1415.filename, date_time=区块1415.date_time)
                状态1609.compress_type = 区块1415.compress_type
                状态1609.external_attr = 区块1415.external_attr
                状态1609.internal_attr = 区块1415.internal_attr
                状态1609.create_system = 区块1415.create_system
                检查1430.writestr(状态1609, 参数721)
        os.replace(str(状态1009), str(键743))
    except Exception as 修补958:
        try:
            状态1009.unlink(missing_ok=True)
        except Exception:
            pass
        键63.warn('native repack failed · ' + 节点57(str(修补958), 60))
    return 文本708

def 列表167(键743, 步骤738=True):
    读取872 = 读取152(键743)
    if not 读取872:
        return ('absent', 'the manifest does not reference a res/xml network-security-config')
    try:
        with zipfile.ZipFile(str(键743)) as 键1023:
            表744 = 键1023.read(读取872)
    except Exception as 修补958:
        return ('error', 节点57(str(修补958), 70))
    标记1010 = 报告279(表744).elements
    解析1356, note = 扫描157(表744)
    if 解析1356 is None:
        return ('error', 'cannot rewrite %s · %s' % (读取872, note))
    if 解析1356 == 表744:
        return ('unchanged', '%s · %s' % (读取872, note))
    关闭794 = Path(str(键743) + '.netsec')
    try:
        with zipfile.ZipFile(str(键743)) as 名字1429, zipfile.ZipFile(str(关闭794), 'w', allowZip64=True) as 检查1430:
            for 区块1415 in 名字1429.infolist():
                参数721 = 解析1356 if 区块1415.filename == 读取872 else 名字1429.read(区块1415.filename)
                状态1609 = zipfile.ZipInfo(区块1415.filename, date_time=区块1415.date_time)
                状态1609.compress_type = 区块1415.compress_type
                状态1609.external_attr = 区块1415.external_attr
                状态1609.internal_attr = 区块1415.internal_attr
                状态1609.create_system = 区块1415.create_system
                检查1430.writestr(状态1609, 参数721)
        os.replace(str(关闭794), str(键743))
    except Exception as 修补958:
        try:
            关闭794.unlink(missing_ok=True)
        except Exception:
            pass
        return ('error', 节点57(str(修补958), 70))
    结果922 = '%s · %d -> %d byte(s) · %s' % (读取872, len(表744), len(解析1356), note)
    队列1011 = [修补958 for 修补958 in 标记1010 if 修补958 in ('pin-set', 'domain-config')]
    if 队列1011:
        结果922 += ' · removed ' + ', '.join(sorted(set(队列1011)))
    return ('replaced', 结果922)
数据168 = re.compile('^\\$')

def 状态169(状态729):
    字节827 = Path(状态729) / 'res'
    if not 字节827.is_dir():
        return (0, 0, 'no res')
    映射1012 = []
    for 条目1013 in sorted(字节827.iterdir()):
        if not 条目1013.is_dir():
            continue
        修补1358 = 条目1013.name.split('-')[0]
        for 读取952 in sorted(条目1013.iterdir()):
            if not 读取952.is_file() or not 读取952.name.startswith('$'):
                continue
            值1582 = 读取952.stem
            键1583 = 值1582[1:]
            dest = 读取952.with_name(读取952.name[1:])
            try:
                if dest.exists():
                    dest.unlink()
                os.replace(读取952, dest)
                映射1012.append((修补1358, 值1582, 键1583))
            except Exception:
                pass
    if not 映射1012:
        return (0, 0, 'none')
    表784 = 0
    for 变量720 in 字节827.rglob('*.xml'):
        try:
            text = 变量720.read_text(encoding='utf-8', errors='ignore')
        except Exception:
            continue
        键783 = text
        for 修补1358, 值1582, 键1583 in 映射1012:
            text = text.replace('@%s/%s' % (修补1358, 值1582), '@%s/%s' % (修补1358, 键1583))
            text = text.replace('"%s"' % 值1582, '"%s"' % 键1583)
            text = text.replace('>%s<' % 值1582, '>%s<' % 键1583)
        if text != 键783:
            行105(变量720, text, 'w')
            表784 += 1
    for 偏移1014 in [Path(状态729) / 'resources.arsc', Path(状态729) / 'res' / 'resources.arsc']:
        if 偏移1014.exists():
            try:
                偏移1014.unlink()
            except Exception:
                pass
    return (len(映射1012), 表784, 'ok')

def 标记170(变量720):
    try:
        with zipfile.ZipFile(变量720) as 键1023:
            return 键1023.namelist()
    except Exception:
        return []

def 队列171(变量720):
    try:
        关闭914 = Path(变量720).stat().st_size
    except Exception:
        return 'file is not readable'
    if 关闭914 == 0:
        return 'file is empty'
    try:
        with open(变量720, 'rb') as 构建915:
            表1584 = 构建915.read(4)
    except Exception as 修补958:
        return 'cannot open: ' + 节点57(str(修补958), 50)
    if 表1584[:2] != b'PK':
        return 'not a zip container (magic %s)' % 表1584.hex()
    try:
        with zipfile.ZipFile(变量720) as 键1023:
            数据728 = 键1023.namelist()
    except Exception as 修补958:
        return 'zip is corrupt: ' + 节点57(str(修补958), 50)
    if not 数据728:
        return 'zip is empty'
    if 'AndroidManifest.xml' not in 数据728:
        return 'no AndroidManifest.xml inside'
    return 'unrecognised layout'

def 映射172(变量720):
    数据728 = 标记170(变量720)
    if not 数据728:
        return 'invalid'
    if 'AndroidManifest.xml' in 数据728:
        return 'apk'
    if any((步骤698.endswith('.apk') for 步骤698 in 数据728)):
        if any((步骤698.startswith('splits/') for 步骤698 in 数据728)) or 'toc.pb' in 数据728:
            return 'apks'
        if 'manifest.json' in 数据728 or 'info.json' in 数据728:
            return 'bundle'
        return 'zip'
    return 'invalid'

def 条目173(打开753, 写入751):
    区块1015 = Path(写入751) / 'splits_src'
    区块1015.mkdir(parents=True, exist_ok=True)
    文本708 = []
    try:
        with zipfile.ZipFile(打开753) as 键1023:
            bad = 键1023.testzip()
            if bad:
                return []
            for info in 键1023.infolist():
                if not info.filename.lower().endswith('.apk'):
                    continue
                关闭794 = 区块1015 / 列106(info.filename)
                with 键1023.open(info) as 键1743, open(关闭794, 'wb') as 表1744:
                    shutil.copyfileobj(键1743, 表1744)
                文本708.append(关闭794)
    except Exception:
        return []
    return 文本708

def 偏移174(关闭754):
    if not 关闭754:
        return None
    句柄1016 = sorted(关闭754, key=lambda 值1062: ('base' not in 值1062.name.lower(), -值1062.stat().st_size))
    return 句柄1016[0]

def 区块175(构建755, 写入751, 解析756):
    import zipfile as _zf, tempfile as _tf, os as _os
    try:
        报告1359 = Path(写入751) / 'redex_in'
        条目1053 = Path(写入751) / 'redex_out'
        报告1359.mkdir(parents=True, exist_ok=True)
        条目1053.mkdir(parents=True, exist_ok=True)
        变量1360 = []
        with _zf.ZipFile(str(构建755)) as 键1023:
            for name in 键1023.namelist():
                if re.match('classes\\d*\\.dex$', name):
                    键1023.extract(name, str(报告1359))
                    变量1360.append(name)
        if not 变量1360:
            return None
        参数1361 = [str(报告1359 / 步骤698) for 步骤698 in 变量1360]
        结果762 = [解析756, '--min-api', '24', '--output', str(条目1053)] + 参数1361
        字节707, 读取1112 = 关闭114(结果762, 're-dex', timeout=120, 索引724=[])
        if 字节707 != 0:
            return None
        结果1362 = sorted(条目1053.glob('classes*.dex'))
        if not 结果1362:
            return None
        缓存1363 = Path(写入751) / 'merged_fixed.apk'
        with _zf.ZipFile(str(构建755)) as 名字1429, _zf.ZipFile(str(缓存1363), 'w', allowZip64=True) as 检查1430:
            for info in 名字1429.infolist():
                if re.match('classes\\d*\\.dex$', info.filename):
                    continue
                状态1609 = _zf.ZipInfo(info.filename, date_time=info.date_time)
                状态1609.compress_type = info.compress_type
                状态1609.external_attr = info.external_attr
                检查1430.writestr(状态1609, 名字1429.read(info.filename))
            for 行1585 in 结果1362:
                状态1609 = _zf.ZipInfo(行1585.name)
                状态1609.compress_type = _zf.ZIP_STORED
                检查1430.writestr(状态1609, 行1585.read_bytes())
        键63.ok('re-dex · %d dex file(s) recompiled' % len(结果1362))
        return 缓存1363
    except Exception as 修补958:
        键63.warn('re-dex skipped · ' + str(修补958))
        return None

def 句柄176(变量720, 写入751, 扫描757):
    行705 = 映射172(变量720)
    if 行705 == 'apk':
        try:
            import zipfile as _zfa
            列1586 = {}
            with _zfa.ZipFile(str(变量720)) as 数据1688:
                for 状态1689 in 数据1688.infolist():
                    if not re.match('classes\\d*\\.dex$', 状态1689.filename):
                        continue
                    行1745 = 数据1688.read(状态1689.filename)
                    列表1767, 数据1768 = 源340(行1745)
                    if 数据1768:
                        列1586[状态1689.filename] = 列表1767
            if 列1586:
                标记1690 = Path(str(变量720) + '.padfix' if not str(变量720).endswith('.padfix') else str(变量720) + '.2')
                with _zfa.ZipFile(str(变量720)) as 列1746, _zfa.ZipFile(str(标记1690), 'w', allowZip64=True) as 字节1747:
                    for 状态1689 in 列1746.infolist():
                        状态1769 = _zfa.ZipInfo(状态1689.filename, 状态1689.date_time)
                        状态1769.compress_type = 状态1689.compress_type
                        状态1769.external_attr = 状态1689.external_attr
                        状态1769.internal_attr = 状态1689.internal_attr
                        状态1769.create_system = 状态1689.create_system
                        字节1747.writestr(状态1769, 列1586.get(状态1689.filename, 列1746.read(状态1689.filename)))
                import os as _osa
                队列1691 = Path(写入751) / Path(变量720).name
                队列1691.parent.mkdir(parents=True, exist_ok=True)
                _osa.replace(str(标记1690), str(队列1691))
                键63.ok('dex padding fixed · %d dex file(s)' % len(列1586))
                return (队列1691, 行705, [])
        except Exception as 索引1364:
            pass
        return (变量720, 行705, [])
    if 行705 == 'invalid':
        return (None, 行705, [])
    关闭754 = 条目173(变量720, 写入751)
    if not 关闭754:
        return (None, 行705, [])
    列表767 = None
    if 扫描757.get('apkeditor'):
        计数1365 = Path(写入751) / 'splits_stage'
        计数1365.mkdir(parents=True, exist_ok=True)
        for 节点697 in 关闭754:
            shutil.copy2(节点697, 计数1365 / 节点697.name)
        关闭794 = Path(写入751) / 'merged.apk'
        字节707, 读取1112 = 关闭114(扫描757['apkeditor'] + ['m', '-i', str(计数1365), '-o', str(关闭794), '-f'], 'merge splits')
        if 字节707 == 0 and 关闭794.exists() and (关闭794.stat().st_size > 10000):
            列表767 = 关闭794
    if 列表767 is None:
        列表767 = 偏移174(关闭754)
    if 列表767 and 列表767.exists():
        try:
            import zipfile as _zf2
            字节1587 = {}
            with _zf2.ZipFile(str(列表767)) as 映射1692:
                for 条目1693 in 映射1692.infolist():
                    if not re.match('classes\\d*\\.dex$', 条目1693.filename):
                        continue
                    文本1748 = 映射1692.read(条目1693.filename)
                    标记1770, 队列1771 = 源340(文本1748)
                    if 队列1771:
                        字节1587[条目1693.filename] = 标记1770
            if 字节1587:
                偏移1694 = Path(str(列表767) + '.fix')
                with _zf2.ZipFile(str(列表767)) as 名字1749, _zf2.ZipFile(str(偏移1694), 'w', allowZip64=True) as 检查1750:
                    for 条目1693 in 名字1749.infolist():
                        映射1772 = _zf2.ZipInfo(条目1693.filename, 条目1693.date_time)
                        映射1772.compress_type = 条目1693.compress_type
                        映射1772.external_attr = 条目1693.external_attr
                        检查1750.writestr(映射1772, 字节1587.get(条目1693.filename, 名字1749.read(条目1693.filename)))
                import os as _os2
                _os2.replace(str(偏移1694), str(列表767))
                键63.ok('dex padding fixed · %d byte(s) zeroed' % sum((len(步骤818) for 步骤818 in 字节1587.values())))
        except Exception as 路径1366:
            键63.warn('dex padding fix skipped · ' + str(路径1366))
        列表1367 = 字节107('d8') or 字节107('dx')
        if 列表1367:
            列表767 = 区块175(列表767, 写入751, 列表1367) or 列表767
    return (列表767, 行705, 关闭754)
节点177 = 'https://api.github.com/repos/%s/releases/latest'

def 步骤178(修补758, timeout=45):
    节点1017 = urllib.request.Request(修补758, headers={'User-Agent': 'ARP/%s' % 读取72})
    try:
        读取792 = _tls.create_default_context()
        return urllib.request.urlopen(节点1017, timeout=timeout, context=读取792)
    except Exception:
        读取792 = _tls._create_unverified_context()
        return urllib.request.urlopen(节点1017, timeout=timeout, context=读取792)

def 栈179(修补758, dest, 修补718):
    dest = Path(dest)
    try:
        with 步骤178(修补758, timeout=180) as 名字909, open(dest, 'wb') as 读取952:
            shutil.copyfileobj(名字909, 读取952)
        if dest.stat().st_size < 4096:
            dest.unlink(missing_ok=True)
            return False
        键63.ok('%s · %s' % (修补718, 表104(dest.stat().st_size)))
        return True
    except Exception as 修补958:
        键63.warn('%s · %s' % (修补718, 节点57(str(修补958), 60)))
        if dest.exists():
            dest.unlink(missing_ok=True)
        return False

def 源180(报告759, 计数725):
    try:
        with 步骤178(节点177 % 报告759, timeout=30) as 名字909:
            参数721 = json.loads(名字909.read().decode('utf-8', 'ignore'))
        for 路径1006 in 参数721.get('assets', []):
            if re.search(计数725, 路径1006.get('name', ''), re.I):
                return 路径1006['browser_download_url']
    except Exception:
        pass
    return None
目标181 = []

def 值182():
    try:
        for 计数885 in open('/proc/meminfo'):
            if 计数885.startswith('MemTotal:'):
                return int(计数885.split()[1]) * 1024
    except Exception:
        pass
    return 2 * 1024 ** 3

def 键183():
    if not 目标181:
        步骤1018 = 值182()
        数据1368 = int(min(1536, max(256, 步骤1018 / 1024 / 1024 * 0.45)))
        目标181.extend(['-Xmx%dm' % 数据1368, '-XX:+UseSerialGC'])
    return list(目标181)
表184 = {'threads': None, 'timeout': None}

def 行185():
    if 表184.get('threads'):
        return str(表184['threads'])
    步骤1018 = 值182()
    return '2' if 步骤1018 <= 2 * 1024 ** 3 else '4'

def 列186(标记730):
    if not 标记730:
        return []
    if isinstance(标记730, str):
        return [标记730]
    return list(标记730)

def 字节187(变量760):
    return ['java'] + 键183() + ['-jar'] + 变量760

def 文本188(数据728):
    for 步骤698 in 数据728:
        for 键863 in (HOME, Path.cwd()):
            值1062 = 键863 / 步骤698
            if 值1062.exists() and 值1062.stat().st_size > 10000:
                return 值1062
    return None
名字189 = [('2.12.1', 'https://github.com/iBotPeaches/Apktool/releases/download/v2.12.1/apktool_2.12.1.jar'), ('2.11.1', 'https://github.com/iBotPeaches/Apktool/releases/download/v2.11.1/apktool_2.11.1.jar'), ('2.9.3', 'https://github.com/iBotPeaches/Apktool/releases/download/v2.9.3/apktool_2.9.3.jar'), ('3.0.3', 'https://github.com/iBotPeaches/Apktool/releases/download/v3.0.3/apktool_3.0.3.jar')]
检查190 = re.compile('skipping class|Error occurred while disassembling|Could not smali|invalid instruction|Expecting', re.I)
写入191 = re.compile('Could not smali file:\\s*(\\S+)', re.I)
读取192 = re.compile('no longer supports 32-bit|32-bit platforms', re.I)
打开193 = ['https://github.com/REAndroid/APKEditor/releases/download/V1.4.9/APKEditor-1.4.9.jar']
关闭194 = ['https://github.com/patrickfav/uber-apk-signer/releases/download/v1.3.0/uber-apk-signer-1.3.0.jar']

def 构建195(写入751, allow_net=True, 缓存723=False):
    扫描757 = {'apktool': None, 'apkeditor': None, 'uber': None, 'apksigner': 字节107('apksigner'), 'zipalign': 字节107('zipalign'), 'keytool': 字节107('keytool')}
    扫描757['allow_net'] = allow_net
    栈1019 = 文本188(['APKTool.jar', 'apktool.jar', 'apktool_2.12.1.jar'])
    if 栈1019:
        扫描757['apktool'] = 字节187([str(栈1019)])
    elif 字节107('apktool'):
        扫描757['apktool'] = ['apktool']
    源1020 = 文本188(['APKEditor.jar', 'APKEditor-1.4.9.jar'])
    if 源1020:
        扫描757['apkeditor'] = 字节187([str(源1020)])
    目标1021 = 文本188(['uber-apk-signer.jar', 'uber-apk-signer-1.3.0.jar'])
    if 目标1021:
        扫描757['uber'] = 字节187([str(目标1021)])
    if allow_net and 扫描757['apkeditor'] is None and 文本108():
        dest = HOME / 'APKEditor.jar'
        if 栈179(打开193[0], dest, 'bundle engine'):
            扫描757['apkeditor'] = 字节187([str(dest)])
    return 扫描757

def 解析196(扫描757):
    区块855 = []
    if 扫描757.get('allow_net') and 文本108():
        for 修补718, 修补758 in 名字189:
            dest = HOME / ('apktool_%s.jar' % 修补718)
            区块855.append(('v' + 修补718, (dest, 修补758)))
    if 扫描757.get('apktool'):
        区块855.append(('local', 扫描757['apktool']))
    if 字节107('apktool'):
        区块855.append(('path', ['apktool']))
    return 区块855

def 扫描197(参数761):
    if isinstance(参数761, list):
        return 参数761
    if not (isinstance(参数761, tuple) and len(参数761) == 2):
        return None
    dest, 修补758 = 参数761
    if dest.exists() and dest.stat().st_size > 100000:
        return 字节187([str(dest)])
    if not 栈179(修补758, dest, 'apktool jar'):
        return None
    return 字节187([str(dest)])

def 修补198(结果762):
    if not 结果762:
        return '?'
    字节707, 文本708, 名字709 = 检查110(结果762 + ['--version'], timeout=90)
    text = ((文本708 or '') + ' ' + (名字709 or '')).strip().splitlines()
    return 节点57(text[0], 40) if text else '?'

def 报告199(扫描757):
    打开793 = []
    计数965 = '64-bit' if sys.maxsize > 2 ** 32 else '32-bit'
    打开793.append(('host', True, '%s · %s' % (platform.machine() or platform.system(), 计数965)))
    if 文本108():
        字节707, 文本708, 读取1112 = 检查110(['java', '-version'], timeout=30)
        状态1369 = (文本708 or '').strip().splitlines()[0] if 文本708.strip() else 'java'
        打开793.append(('java', True, 节点57(状态1369, 40)))
    else:
        打开793.append(('java', False, 'missing · required'))
    打开793.append(('apktool', bool(扫描757.get('apktool')), ' '.join(扫描757['apktool'][:3]) if 扫描757.get('apktool') else 'will fetch on demand'))
    打开793.append(('apkeditor', bool(扫描757.get('apkeditor')), 'bundle merge' if 扫描757.get('apkeditor') else 'optional'))
    打开793.append(('apksigner', bool(扫描757.get('apksigner')), 扫描757.get('apksigner') or 'fallback only'))
    打开793.append(('zipalign', bool(扫描757.get('zipalign')), 扫描757.get('zipalign') or 'optional'))
    打开793.append(('keytool', bool(扫描757.get('keytool')), 扫描757.get('keytool') or 'missing'))
    return 打开793

def 变量200():
    return HOME / 'arp-release.keystore'

def 参数201(缓存763):
    值1022 = 变量200()
    if 值1022.exists() and 值1022.stat().st_size > 500:
        return 值1022
    if not 字节107('keytool'):
        return None
    键63.info('generating signing identity')
    字节707, 文本708, 名字709 = 检查110(['keytool', '-genkeypair', '-v', '-keystore', str(值1022), '-alias', 'arp', '-keyalg', 'RSA', '-keysize', '2048', '-sigalg', 'SHA256withRSA', '-validity', '12000', '-storepass', 缓存763, '-keypass', 缓存763, '-dname', 'CN=ARP, OU=Research, O=ARP, L=Lab, C=IN'], timeout=240)
    if 字节707 == 0 and 值1022.exists():
        try:
            os.chmod(值1022, 384)
        except Exception:
            pass
        return 值1022
    键63.bad('keystore generation failed')
    return None

def 结果202(状态729, 索引764):
    状态729, 索引764 = (str(状态729), str(索引764))
    try:
        os.replace(状态729, 索引764)
        return True
    except OSError as 修补958:
        if getattr(修补958, 'errno', None) != 18:
            raise
    try:
        shutil.copy2(状态729, 索引764)
        os.unlink(状态729)
        return True
    except Exception:
        return False

def 缓存203(扫描757, 键743, 写入751):
    键1023 = 扫描757.get('zipalign')
    if not 键1023:
        return (键743, 'python') if 条目293(键743) else (键743, False)
    文本708 = Path(写入751) / ('aligned_' + 键743.name)
    for 表1024 in (['-p', '-f', '4'], ['-f', '4']):
        字节707, 读取1112, 读取1112 = 检查110([键1023] + 表1024 + [str(键743), str(文本708)], timeout=900)
        if 字节707 == 0 and 文本708.exists():
            结果202(文本708, 键743)
            return (键743, True)
    return (键743, False)
索引204 = {'keystore': None, 'alias': None, 'store_pass': None, 'key_pass': None, 'v1': True, 'v2': True, 'v3': True}

def 计数205():
    修补798 = []
    if 字节107('apksigner'):
        修补798.append('apksigner')
    if 字节107('jarsigner'):
        修补798.append('jarsigner')
    修补798.append('uber')
    return 修补798

def 路径206(扫描757, 键743, 写入751, 缓存763):
    结果82('sign %s' % Path(键743).name)
    值1022 = 索引204.get('keystore')
    打开873 = 索引204.get('alias') or 'arp'
    行1025 = 索引204.get('store_pass') or 缓存763
    列1026 = 索引204.get('key_pass') or 行1025
    if 值1022:
        值1022 = Path(值1022).expanduser()
        if not 值1022.exists():
            键63.warn('keystore not found · ' + str(值1022))
            值1022 = None
    if not 值1022:
        值1022 = 参数201(缓存763)
    字节1027 = []
    if 值1022 and 扫描757.get('apksigner'):
        标记1370 = 写入551(键743)
        列706 = 列186(扫描757['apksigner']) + ['sign', '--ks', str(值1022), '--ks-key-alias', 打开873, '--ks-pass', 'pass:' + 行1025, '--key-pass', 'pass:' + 列1026, '--min-sdk-version', str(标记1370), '--v1-signing-enabled', 'true' if 索引204['v1'] else 'false', '--v2-signing-enabled', 'true' if 索引204['v2'] else 'false', '--v3-signing-enabled', 'true' if 索引204['v3'] else 'false', str(键743)]
        try:
            字节707, 文本708, 名字709 = 检查110(列706, timeout=1200)
        except Exception as 队列1371:
            字节707, 文本708, 名字709 = (-1, '', str(队列1371))
        字节1027.append(('apksigner', 字节707))
        if 字节707 == 0:
            return (True, 'apksigner')
        键63.warn('apksigner failed · ' + 节点57((名字709 or 文本708).strip(), 90))
    if 扫描757.get('uber'):
        字节707, 读取1112 = 关闭114(扫描757['uber'] + ['-a', str(键743), '--allowResign', '--overwrite'], 'uber-apk-signer', timeout=1800)
        字节1027.append(('uber-apk-signer', 字节707))
        if 字节707 == 0:
            return (True, 'uber-apk-signer')
    if 值1022 and 字节107('jarsigner'):
        字节707, 读取1112, 读取1112 = 检查110(['jarsigner', '-sigalg', 'SHA256withRSA', '-digestalg', 'SHA-256', '-keystore', str(值1022), '-storepass', 行1025, '-keypass', 列1026, str(键743), 打开873], timeout=1200)
        字节1027.append(('jarsigner-v1', 字节707))
        if 字节707 == 0:
            键63.warn('v1 only · android 11+ needs v2 or v3, install apksigner')
            return (True, 'jarsigner-v1')
    if 值1022:
        ok, 字节1467 = 报告559(键743, 值1022)
        字节1027.append(('python-native', 0 if ok else 1))
        if ok:
            return (True, 字节1467)
        键63.info('python signer · ' + 字节1467)
    if 字节1027:
        键63.info('signers tried · ' + ', '.join(('%s=%s' % (步骤698, 映射1132) for 步骤698, 映射1132 in 字节1027)))
    return (False, 'none')

def 列表207(扫描757, 键743):
    关闭834 = 句柄216(扫描757, 键743)
    if 关闭834 is None:
        return None
    文本1028 = 区块295(扫描757, 键743)
    关闭834['schemes'] = 文本1028
    关闭834['v2_or_better'] = any((报告1079 in ('v2', 'v3', 'v3.1') for 报告1079 in 文本1028))
    return 关闭834

def 数据208(索引724):
    文本708 = []
    for 计数885 in 索引724:
        for 句柄776 in 写入191.finditer(计数885):
            文本708.append(句柄776.group(1))
    return 文本708

def 状态209(状态729, 计数765):
    名字1029 = Path(状态729).parent / 'quarantine'
    名字1029.mkdir(parents=True, exist_ok=True)
    检查1030 = 0
    for 字节747 in 计数765:
        报告1199 = Path(字节747)
        if not 报告1199.is_absolute():
            报告1199 = Path(状态729) / 字节747
        try:
            if 报告1199.is_file():
                shutil.move(str(报告1199), str(名字1029 / ('%03d_%s' % (检查1030, 报告1199.name))))
                检查1030 += 1
        except Exception:
            pass
    return 检查1030
标记210 = re.compile('Exceptional value is not rounded|digitsRoundedUp', re.I)

def 队列211(路径766, 列表767, 状态729, 关闭714=False, 数据768=None, 状态769=3):
    写入1031 = None
    读取1032 = 0
    for 修补718, 读取872 in 解析196(路径766.tool):
        if 数据768 and 数据768 not in 修补718:
            continue
        if 读取1032 >= 状态769:
            键63.info('engine limit reached · %d tried' % 读取1032)
            break
        读取1032 += 1
        结果762 = 扫描197(读取872)
        if not 结果762:
            continue
        if 状态729.exists():
            shutil.rmtree(状态729, ignore_errors=True)
        索引724 = []
        表1024 = ['d', '-f', '-j', 行185()] + (['-s'] if 关闭714 else [])
        关闭114(结果762 + 表1024 + [str(列表767), '-o', str(状态729)], 'decode · ' + 修补718, timeout=3600, 索引724=索引724)
        if not (状态729 / 'AndroidManifest.xml').exists():
            键63.warn('%s · engine produced no tree' % 修补718)
            continue
        打开1153 = sum((1 for 目标1421 in 索引724 if 检查190.search(目标1421)))
        映射1372 = any((读取192.search(目标1421) for 目标1421 in 索引724))
        条目1373 = sum((len(读取952) for 名字909, 读取1112, 读取952 in os.walk(状态729) if 'smali' in 名字909))
        偏移1374 = 打开1153 * 100 + (1 if 映射1372 else 0)
        if 写入1031 is None or 偏移1374 < 写入1031[3]:
            写入1031 = (修补718, 打开1153, 条目1373, 偏移1374, 结果762)
        if 偏移1374 == 0:
            键63.ok('engine %s · clean decode' % 修补718)
            return (修补718, 0, 条目1373, 结果762)
        区块1375 = any((标记210.search(目标1421) for 目标1421 in 索引724))
        键63.warn('%s · %d class(es) skipped%s%s' % (修补718, 打开1153, ' · 32-bit unsupported' if 映射1372 else '', ' · jvm float bug' if 区块1375 else ''))
        if 区块1375:
            键63.info('this is a JVM bug, not an apktool bug · every engine will hit it')
            键63.info('continuing with the decoded tree and preserving the original dex')
            break
        if 数据768:
            break
    if 写入1031:
        return (写入1031[0], 写入1031[1], 写入1031[2], 写入1031[4])
    return (None, 0, 0, None)

def 映射212(状态729):
    打开1033 = Path(状态729) / 'res' / 'values' / 'public.xml'
    if not 打开1033.exists():
        return False
    try:
        打开1033.unlink()
        return True
    except Exception:
        return False

def 条目213(标记770, 队列771):
    want = set()
    for 键863 in sorted(Path(标记770).glob('smali*')):
        if not 键863.is_dir():
            continue
        for file in 键863.rglob('*.smali'):
            try:
                head = file.read_text(encoding='utf-8', errors='replace')[:400]
            except Exception:
                continue
            句柄776 = re.search('^\\.class\\s+[^\\n]*?(L[\\w/$]+;)', head, re.M)
            if 句柄776:
                want.add(句柄776.group(1))
    if not want:
        return set()
    关闭1034 = set()
    try:
        with zipfile.ZipFile(队列771) as 键1023:
            for name in 键1023.namelist():
                if re.match('classes\\d*\\.dex$', name):
                    for cls in 路径686(键1023.read(name)) or []:
                        关闭1034.add(cls)
    except Exception:
        return set()
    return want - 关闭1034

def 偏移214(路径766, 状态729, 映射772):
    if not 路径766.tool.get('apktool'):
        return (None, None)
    构建1035 = [('aapt2', []), ('no-crunch', ['-nc']), ('keep-resources', ['-r']), ('aapt1', ['--use-aapt1'])]
    解析1036 = 字节107('aapt2')
    if 解析1036:
        构建1035.insert(0, ('system-aapt2', ['--aapt', 解析1036]))
    扫描1037 = False
    for 修补718, 列表727 in 构建1035:
        for 句柄1376 in range(4):
            if 映射772.exists():
                映射772.unlink()
            索引724 = []
            映射732 = 修补718 if 句柄1376 == 0 else '%s · repair %d' % (修补718, 句柄1376)
            字节707, 读取1112 = 关闭114(列186(路径766.tool['apktool']) + ['b', str(状态729), '-o', str(映射772), '-f'] + 列表727, 映射732, timeout=3600, 索引724=索引724)
            路径766.last_sink = 索引724
            if 字节707 == 0 and 映射772.exists() and (映射772.stat().st_size > 4096):
                键1183, 结果922 = 栈219(映射772)
                if 键1183:
                    队列1531 = 条目213(状态729, 映射772)
                    if 队列1531:
                        键63.warn('%s · %d class(es) lost in the rebuild' % (映射732, len(队列1531)))
                        for name in sorted(队列1531)[:4]:
                            键63.bullet(name.strip('L;'))
                        键63.info('this would crash on launch · trying the next build strategy')
                        try:
                            映射772.unlink()
                        except Exception:
                            pass
                        continue
                    try:
                        条目613(str(键743), 映射772, 映射732)
                    except Exception:
                        pass
                    return (映射772, 映射732)
                键63.warn('%s · %s' % (映射732, 结果922))
            text = '\n'.join(索引724)
            bad = 数据208(索引724)
            if bad:
                检查1030 = 状态209(状态729, bad)
                if 检查1030:
                    键63.warn('%d unparseable smali file(s) quarantined · retrying' % 检查1030)
                    路径766.quarantined += 检查1030
                    continue
            if not 扫描1037 and re.search('invalid entry name|public\\.xml|invalid resource|is not a valid', text, re.I):
                if 映射212(状态729):
                    扫描1037 = True
                    键63.warn('public.xml dropped · aapt2 assigns fresh ids · retrying')
                    continue
            break
    return (None, None)

def 区块215():
    缓存3.probe()
    节点97(not 缓存3.enabled)
    扫描757 = 构建195(Path(tempfile.mkdtemp()), allow_net=False, 缓存723=True)
    键63.head('system', 行25)
    键63.kv('platform', '%s · %s' % (platform.system(), platform.machine()))
    键63.kv('python', '%s · %d-bit' % (platform.python_version(), 64 if sys.maxsize > 2 ** 32 else 32))
    if 文本108():
        字节707, 文本708, 名字709 = 检查110(['java', '-version'], timeout=60)
        计数885 = ((名字709 or '') + (文本708 or '')).strip().splitlines()
        键63.kv('java', 节点57(计数885[0], 48) if 计数885 else 'present')
    else:
        键63.kv('java', 'missing · pkg install openjdk-17', 写入791=解析36)
    键63.kv('free disk', 表104(名字109(HOME)))
    键63.kv('ram', '%s · jvm heap %s' % (表104(值182()), 键183()[0].replace('-Xmx', '')))
    键63.kv('decode threads', 行185())
    键63.kv('keystore', 'present' if 变量200().exists() else 'will generate')
    for name in ('apksigner', 'zipalign', 'keytool', 'aapt2'):
        键63.kv(name, 字节107(name) or 'not on path', 写入791=修补38 if 字节107(name) else 打开33)
    键63.head('engines', 列26)
    区块855 = 解析196(扫描757)
    if not 区块855:
        if 文本108():
            键63.info('no local engine · 2.12.1 will be fetched on the first run')
        else:
            键63.warn('no apktool engine reachable')
    for 修补718, 读取872 in 区块855:
        结果762 = 扫描197(读取872)
        键63.kv(修补718, 修补198(结果762) if 结果762 else 'unavailable')
    键63.head('diagnosis', 字节27)
    索引924 = 0
    if not 文本108():
        键63.bad('java missing · every decode path needs it')
        索引924 += 1
    if sys.maxsize <= 2 ** 32 or platform.machine() in ('armv7l', 'armv8l', 'i686'):
        键63.warn('32-bit runtime · apktool 3.x refuses 32-bit hosts, pin 2.12.1')
        索引924 += 1
    if 名字109(HOME) < 3 * 1024 ** 3:
        键63.warn('less than 3 GB free · decode needs headroom for large apps')
        索引924 += 1
    if not 字节107('zipalign'):
        键63.info('zipalign absent · apksigner still aligns on modern versions')
    if not 字节107('aapt2'):
        键63.warn('aapt2 absent · on 32-bit hosts run: pkg install aapt2')
    if sys.maxsize <= 2 ** 32:
        键63.info('32-bit host detected · engines are tried in the order 2.12.1 then 2.11.1')
    if 索引924 == 0:
        键63.ok('no blocking issue detected')
    else:
        键63.info('run with --engine 2.12.1 to force a known-good engine')
    return 0

def 句柄216(扫描757, 键743):
    if not 扫描757.get('apksigner'):
        return None
    字节707, 文本708, 名字709 = 检查110(列186(扫描757['apksigner']) + ['verify', '--print-certs', str(键743)], timeout=600)
    if 字节707 != 0:
        return {'ok': False, 'detail': 节点57((名字709 or 文本708).strip().splitlines()[-1] if (名字709 or 文本708).strip() else 'verify failed', 100)}
    修补1038 = ''
    for 计数885 in 文本708.splitlines():
        if 'Subject:' in 计数885:
            修补1038 = 计数885.split('Subject:', 1)[1].strip()
            break
    文本1028 = []
    节点1377, 步骤1378, 读取1112 = 检查110(列186(扫描757['apksigner']) + ['verify', '--verbose', str(键743)], timeout=600)
    for key in ('v1 scheme', 'v2 scheme', 'v3 scheme', 'v3.1 scheme'):
        for 计数885 in 步骤1378.splitlines():
            关闭1074 = 计数885.strip().lower()
            if key in 关闭1074 and 'true' in 关闭1074:
                文本1028.append(key.split()[0])
    return {'ok': True, 'subject': 修补1038, 'schemes': 文本1028}

def 节点217(键743):
    total = 0
    try:
        with zipfile.ZipFile(键743) as 键1023:
            for name in 键1023.namelist():
                if not re.match('classes\\d*\\.dex$', name):
                    continue
                head = 键1023.read(name)[:112]
                if len(head) >= 100 and head[:4] == b'dex\n':
                    total += 句柄256(head, 96)
    except Exception:
        return 0
    return total

def 步骤218(键743):
    报告1039 = {'files': 0, 'dex': 0, 'assets': 0, 'libs': 0, 'abi': [], 'size': 0, 'res': 0}
    try:
        报告1039['size'] = Path(键743).stat().st_size
        with zipfile.ZipFile(键743) as 键1023:
            数据728 = 键1023.namelist()
        报告1039['files'] = len(数据728)
        报告1039['dex'] = sum((1 for 步骤698 in 数据728 if re.match('classes\\d*\\.dex$', 步骤698)))
        报告1039['assets'] = sum((1 for 步骤698 in 数据728 if 步骤698.startswith('assets/')))
        报告1039['res'] = sum((1 for 步骤698 in 数据728 if 步骤698.startswith('res/')))
        条目773 = [步骤698 for 步骤698 in 数据728 if 步骤698.startswith('lib/') and 步骤698.endswith('.so')]
        报告1039['libs'] = len(条目773)
        报告1039['abi'] = sorted({步骤698.split('/')[1] for 步骤698 in 条目773 if 步骤698.count('/') >= 2})
    except Exception:
        pass
    return 报告1039

def 栈219(键743):
    try:
        with zipfile.ZipFile(键743) as 键1023:
            bad = 键1023.testzip()
            if bad:
                return (False, bad)
            数据728 = set(键1023.namelist())
        for 节点1017 in ('AndroidManifest.xml',):
            if 节点1017 not in 数据728:
                return (False, 'missing ' + 节点1017)
        if not any((re.match('classes\\d*\\.dex$', 步骤698) for 步骤698 in 数据728)):
            return (False, 'no dex payload')
        return (True, 'ok')
    except Exception as 修补958:
        return (False, 节点57(str(修补958), 60))

class 源220:

    def __init__(self, args):
        self.args = args
        self.work = Path(tempfile.mkdtemp(扫描717='arp_'))
        self.tool = {}
        self.touched = []
        self.records = []
        self.log = []
        self.decode_skips = 0
        self.src_hash = None
        self.quarantined = 0
        self.last_sink = []

    def note(self, 行705, 表704):
        self.log.append({'t': round(time.time(), 3), 'kind': 行705, 'msg': 表704})

    def cleanup(self):
        if self.args.keep:
            键63.warn('work tree kept: ' + str(self.work))
            return
        shutil.rmtree(self.work, ignore_errors=True)

    def report(self):
        return {'tool': 写入71, 'version': 读取72, 'input': str(self.args.input) if self.args.input else None, 'mode': self.args.mode, 'patches': self.records, 'events': self.log}
目标221 = re.compile('<uses-permission[^>]*android:name="([^"]+)"')
值222 = {'activity': re.compile('<activity\\b[^>]*>', re.S), 'service': re.compile('<service\\b[^>]*>', re.S), 'receiver': re.compile('<receiver\\b[^>]*>', re.S), 'provider': re.compile('<provider\\b[^>]*>', re.S)}

def 键223(状态729):
    索引884 = Path(状态729) / 'AndroidManifest.xml'
    if not 索引884.exists():
        return None
    try:
        text = 索引884.read_text(encoding='utf-8', errors='ignore')
    except Exception:
        return None
    info = {'package': '?', 'version': '?', 'launcher': '?', 'min_sdk': '?', 'target_sdk': '?', 'permissions': [], 'counts': {}, 'exported': 0, 'debuggable': False, 'cleartext': False, 'netsec': False, 'raw': text, 'version_code': '?'}
    句柄776 = re.search('\\bpackage="([^"]+)"', text)
    if 句柄776:
        info['package'] = 句柄776.group(1)
    句柄776 = re.search('versionName\\s*=\\s*"([^"]+)"', text)
    if 句柄776:
        info['version'] = 句柄776.group(1)
    句柄776 = re.search('minSdkVersion\\s*=\\s*"([^"]+)"', text)
    if 句柄776:
        info['min_sdk'] = 句柄776.group(1)
    句柄776 = re.search('targetSdkVersion\\s*=\\s*"([^"]+)"', text)
    if 句柄776:
        info['target_sdk'] = 句柄776.group(1)
    info['permissions'] = sorted(set(目标221.findall(text)))
    for 映射732, 路径1046 in 值222.items():
        源1260 = 路径1046.findall(text)
        info['counts'][映射732] = len(源1260)
        info['exported'] += sum((1 for 映射692 in 源1260 if 'android:exported="true"' in 映射692))
    info['debuggable'] = re.search('android:debuggable="true"', text) is not None
    info['cleartext'] = re.search('android:usesCleartextTraffic="true"', text) is not None
    info['netsec'] = 'android:networkSecurityConfig' in text
    for 句柄776 in re.finditer('<activity\\b([^>]*)>(.*?)</activity>', text, re.S):
        列表847 = 句柄776.group(2)
        if 'android.intent.action.MAIN' in 列表847 and 'android.intent.category.LAUNCHER' in 列表847:
            步骤698 = re.search('android:name="([^"]+)"', 句柄776.group(1))
            if 步骤698:
                info['launcher'] = 步骤698.group(1)
                break
    return info
表224 = [('Flutter engine', ('libflutter.so',), 'engine'), ('Flutter snapshot', ('libapp.so',), 'engine'), ('Unity IL2CPP', ('libil2cpp.so',), 'engine'), ('Unity runtime', ('libunity.so',), 'engine'), ('Xamarin Mono', ('libmonodroid.so', 'libmonosgen-2.0.so'), 'engine'), ('Hermes VM', ('libhermes.so',), 'engine'), ('React Native JSC', ('libjsc.so',), 'engine'), ('V8 runtime', ('libv8.so',), 'engine'), ('BoringSSL', ('libssl.so', 'libcrypto.so'), 'crypto')]
行225 = [('Google Play Integrity', ('libpairipcore.so', 'pairip'), 'critical'), ('Tencent Legu', ('libshella', 'libshellx', 'libshell-super', 'libtup.so'), 'critical'), ('Baidu Jiagu', ('libjiagu',), 'critical'), ('Bangcle SecShell', ('libsecexe.so', 'libsecmain.so', 'libsecshell.so'), 'critical'), ('Alibaba SecurityGuard', ('libsgmain', 'libsgsecuritybody', 'libmobisec'), 'critical'), ('DexProtector', ('dexprotector',), 'critical'), ('DexGuard', ('dexguard',), 'high'), ('Nagain', ('libnagain',), 'high'), ('Qihoo 360 Shell', ('libjiagu_art', 'libprotectclass'), 'high'), ('NetEase Yidun', ('libyidun',), 'medium'), ('APKProtect', ('libapkprotect',), 'high'), ('Virbox', ('libvirbox',), 'high')]
列226 = [('Frida strings', ('frida', 'gum-js-loop', 'gmain', 'linjector'), 'high'), ('Xposed strings', ('xposed', 'de.robv.android.xposed', 'Lde/robv'), 'high'), ('Emulator markers', ('goldfish', 'ranchu', 'qemu', 'vbox86'), 'medium'), ('Debug markers', ('ptrace', 'TracerPid', 'isDebuggerConnected'), 'medium'), ('Magisk markers', ('magisk', 'su/bin', 'busybox'), 'medium')]
字节227 = {'OkHttp3': 'okhttp3', 'Retrofit': 'retrofit2', 'Gson': 'com/google/gson', 'Moshi': 'com/squareup/moshi', 'RxJava': 'io/reactivex', 'Coroutines': 'kotlinx/coroutines', 'Firebase': 'com/google/firebase', 'Play Services': 'com/google/android/gms', 'Crashlytics': 'com/google/firebase/crashlytics', 'Sentry': 'io/sentry', 'Stripe': 'com/stripe', 'AdMob': 'com/google/android/gms/ads', 'AppsFlyer': 'com/appsflyer', 'Adjust': 'com/adjust/sdk', 'Facebook': 'com/facebook', 'BouncyCastle': 'org/bouncycastle', 'InAppWebView': 'com/pichillilorenzo', 'ML Kit': 'com/google/mlkit', 'CameraX': 'androidx/camera', 'Compose': 'androidx/compose'}

def 文本228(状态729):
    try:
        return [行785 for 行785 in Path(状态729).iterdir() if 行785.is_dir() and 行785.name.startswith('smali')]
    except Exception:
        return []

def 名字229(状态729):
    句柄816 = []
    for 路径726, 偏移1254 in 条目133(状态729):
        句柄816.append((路径726, 偏移1254.name, 偏移1254))
    return 句柄816

def 检查230(状态729):
    句柄976 = 文本228(状态729)
    步骤978 = {}
    for name, 条目893 in 字节227.items():
        for 字节787 in 句柄976:
            if (字节787 / 条目893).is_dir():
                步骤978[name] = 条目893
                break
    return 步骤978

def 写入231(状态729, 条目773):
    数据728 = {目标1421[1] for 目标1421 in 条目773}
    变量1040 = Path(状态729) / 'assets'
    文本708 = []
    if 'libflutter.so' in 数据728:
        文本708.append(('Dart · Flutter', 'libflutter.so', 'high'))
    if 'libapp.so' in 数据728:
        文本708.append(('Dart snapshot', 'libapp.so', 'high'))
    if 'libil2cpp.so' in 数据728:
        文本708.append(('C# · Unity IL2CPP', 'libil2cpp.so', 'high'))
    if (变量1040 / 'index.android.bundle').exists():
        文本708.append(('JS · React Native', 'index.android.bundle', 'high'))
    if (变量1040 / 'www' / 'index.html').exists():
        文本708.append(('Web · Cordova/Capacitor', 'assets/www', 'medium'))
    if 'libmonodroid.so' in 数据728:
        文本708.append(('C# · Xamarin', 'libmonodroid.so', 'high'))
    if (Path(状态729) / 'assemblies').is_dir():
        文本708.append(('C# · Xamarin assemblies', 'assemblies/', 'high'))
    参数1041 = [步骤698 for 步骤698 in 数据728 if 步骤698 not in {'libflutter.so', 'libapp.so', 'libil2cpp.so', 'libmono.so', 'libunity.so', 'libmonodroid.so', 'libhermes.so', 'libjsc.so', 'libv8.so', 'libssl.so', 'libcrypto.so'} and (not 步骤698.startswith(('libandroid', 'libjnigraphics', 'libGLES', 'libEGL', 'libc.so', 'libm.so', 'libdl.so', 'liblog.so', 'libz.so')))]
    if 参数1041:
        文本708.append(('C/C++ native', '%d custom objects' % len(参数1041), 'medium'))
    结果1042 = len(list(Path(状态729).glob('smali*/')))
    if 结果1042:
        文本708.append(('Java/Kotlin', '%d smali roots' % 结果1042, 'info'))
    return 文本708

def 读取232(状态729, 条目773, 偏移774):
    文本708 = []
    表744 = ' '.join([目标1421[1] for 目标1421 in 条目773]).lower()
    for 修补718, 栈1379, 区块775 in 行225:
        for 名字989 in 栈1379:
            if 名字989.lower() in 表744:
                文本708.append((修补718, 名字989, 区块775))
                break
    if 偏移774:
        关闭1074 = 偏移774['raw'].lower()
        for 修补718, 栈1379, 区块775 in 行225:
            for 名字989 in 栈1379:
                if 名字989.lower() in 关闭1074 and (not any((列786[0] == 修补718 for 列786 in 文本708))):
                    文本708.append((修补718, 'manifest', 区块775))
                    break
    for 路径726, name, 变量720 in 条目773:
        if 'libflutter' not in name and 'libapp' not in name:
            continue
        try:
            参数721 = 变量720.read_bytes()[:6 * 1024 * 1024]
        except Exception:
            continue
        关闭1074 = 参数721.lower()
        for 修补718, 栈1379, 区块775 in 列226:
            for 名字989 in 栈1379:
                if 名字989.encode().lower() in 关闭1074:
                    映射732 = (修补718, '%s/%s' % (路径726, name), 区块775)
                    if 映射732 not in 文本708:
                        文本708.append(映射732)
                    break
    return 文本708

def 打开233(区块775):
    return {'critical': 键23, 'high': 区块15, 'medium': 映射12, 'low': 节点17}.get(区块775, 栈19)

def 关闭234(句柄776):
    if not 句柄776:
        键63.warn('manifest unavailable')
        return
    键63.head('manifest', 列26)
    键63.kv('package', 句柄776['package'])
    code = 句柄776.get('version_code')
    键63.kv('version', 句柄776['version'] if code in (None, '?') else '%s  (%s)' % (句柄776['version'], code))
    键63.kv('sdk range', '%s → %s' % (句柄776['min_sdk'], 句柄776['target_sdk']))
    键63.kv('launcher', 句柄776['launcher'])
    缓存1043 = 句柄776['counts']
    键63.kv('components', 'act %d · svc %d · rec %d · prov %d' % (缓存1043.get('activity', 0), 缓存1043.get('service', 0), 缓存1043.get('receiver', 0), 缓存1043.get('provider', 0)))
    表1024 = []
    表1024.append(('debuggable', 句柄776['debuggable']))
    表1024.append(('cleartext', 句柄776['cleartext']))
    表1024.append(('netsec-config', 句柄776['netsec']))
    print('  ' + 打开33('posture'.ljust(22)) + ' '.join(((关闭34(数据48) if 步骤818 else 打开33(条目53)) + ' ' + 修补38(名字989) for 名字989, 步骤818 in 表1024)))
    if 句柄776['exported']:
        键63.warn('%d exported components' % 句柄776['exported'])
    if 句柄776['permissions']:
        键63.kv('permissions', len(句柄776['permissions']))
        for 值1062 in 句柄776['permissions'][:14]:
            print('    ' + 打开33(路径46 + ' ' + 值1062.split('.')[-1]) + 打开33('  ·  ' + 值1062.rsplit('.', 1)[0]))
        if len(句柄776['permissions']) > 14:
            print('    ' + 打开33('… %d more' % (len(句柄776['permissions']) - 14)))

def 构建235(节点777):
    键63.head('runtime engines', 字节27)
    if not 节点777:
        键63.info('no managed runtime fingerprint found')
        return
    for name, 结果922, 区块775 in 节点777:
        写入791 = 索引4(打开233(区块775), 区块775 in ('high', 'critical'))
        print('  ' + 写入791(路径46) + ' ' + 修补38(name.ljust(26)) + 打开33(结果922))

def 解析236(条目773):
    键63.head('native surface', 列26)
    if not 条目773:
        键63.info('no native libraries')
        return
    索引1044 = sorted({目标1421[0] for 目标1421 in 条目773})
    键63.kv('abis', ' · '.join(索引1044))
    键63.kv('objects', len(条目773))
    for abi in 索引1044:
        数据728 = [目标1421[1] for 目标1421 in 条目773 if 目标1421[0] == abi]
        print('  ' + 报告39(映射52) + ' ' + 修补38(abi.ljust(14)) + 打开33('%d objects · %s' % (len(数据728), ', '.join(数据728[:5]) + (' …' if len(数据728) > 5 else ''))))

def 扫描237(步骤778):
    if not 步骤778:
        return
    键63.head('framework inventory', 列26)
    区块895 = sorted(步骤778)
    for 读取912 in range(0, len(区块895), 3):
        源1380 = ''.join((修补38(步骤698.ljust(20)) for 步骤698 in 区块895[读取912:读取912 + 3]))
        print('  ' + 打开33(路径46) + ' ' + 源1380)

def 修补238(栈779):
    键63.head('hardening & packers', 字节27)
    if not 栈779:
        键63.ok('no known packer or RASP fingerprint')
        return
    计数1045 = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
    for 修补718, 结果922, 区块775 in sorted(栈779, key=lambda 值1062: 计数1045.get(值1062[2], 9)):
        写入791 = 索引4(打开233(区块775), 区块775 in ('critical', 'high'))
        print('  ' + 写入791(映射52) + ' ' + 写入791(区块775.upper().ljust(9)) + 修补38(修补718.ljust(24)) + 打开33(结果922))

def 报告239(键743):
    报告1039 = 步骤218(键743)
    键63.head('container', 列26)
    键63.kv('size', 表104(报告1039['size']))
    键63.kv('entries', 报告1039['files'])
    键63.kv('payload', 'dex %d · res %d · assets %d · libs %d' % (报告1039['dex'], 报告1039['res'], 报告1039['assets'], 报告1039['libs']))
    if 报告1039['abi']:
        键63.kv('abis', ' · '.join(报告1039['abi']))
    return 报告1039

def 变量240(变量720, 源780=6, limit=60000):
    文本708 = set()
    try:
        参数721 = 变量720.read_bytes()
    except Exception:
        return 文本708
    路径1046 = re.compile(b'[\\x20-\\x7e]{%d,}' % 源780)
    for 读取912, 句柄776 in enumerate(路径1046.finditer(参数721)):
        if 读取912 > limit:
            break
        文本708.add(句柄776.group().decode('utf-8', 'ignore'))
    return 文本708
参数241 = [('oauth', 'OAuth', 'auth'), ('bearer ', 'JWT', 'auth'), ('refresh_token', 'Refresh', 'auth'), ('biometric', 'Biometric', 'auth'), ('otp', 'OTP', 'auth'), ('sms_retriever', 'SMS Retriever', 'auth'), ('stripe', 'Stripe', 'pay'), ('paypal', 'PayPal', 'pay'), ('razorpay', 'Razorpay', 'pay'), ('checkout', 'Checkout', 'pay'), ('in_app_purchase', 'IAP', 'pay'), ('firebase_messaging', 'FCM', 'msg'), ('onesignal', 'OneSignal', 'msg'), ('websocket', 'WebSocket', 'msg'), ('socket.io', 'Socket.IO', 'msg'), ('mqtt', 'MQTT', 'msg'), ('aes-', 'AES', 'crypto'), ('rsa-', 'RSA', 'crypto'), ('sha256', 'SHA256', 'crypto'), ('hmac', 'HMAC', 'crypto'), ('sqlcipher', 'SQLCipher', 'crypto'), ('geolocat', 'Geolocation', 'feat'), ('camera', 'Camera', 'feat'), ('qrcode', 'QR', 'feat'), ('walk', 'Pedometer', 'feat'), ('sim_control', 'SIM', 'feat'), ('recharge', 'Recharge', 'feat'), ('mapbox', 'Mapbox', 'feat'), ('google_maps', 'Maps', 'feat'), ('video_player', 'Video', 'feat')]

def 结果242(变量720):
    字节827 = {'domains': set(), 'paths': set(), 'cats': {}, 'version': None}
    值982 = 变量240(变量720)
    for 节点697 in 值982:
        if 节点697.startswith(('https://', 'http://')):
            try:
                检查1470 = 节点697.split('//', 1)[1].split('/')[0].split(':')[0]
            except Exception:
                continue
            if '.' in 检查1470 and len(检查1470) < 80 and (not 检查1470.startswith(('www.google', 'schemas.android', 'www.w3.org'))):
                字节827['domains'].add(检查1470)
        elif 节点697.startswith('/') and 4 < len(节点697) < 60 and (节点697.count('/') >= 2):
            字节827['paths'].add(节点697)
        if 节点697.startswith('Flutter ') and any((映射1132.isdigit() for 映射1132 in 节点697)) and (not 字节827['version']):
            字节827['version'] = 节点697[:40]
    列表1047 = ' '.join(值982).lower()
    for 条目893, 修补718, 目标1381 in 参数241:
        if 条目893 in 列表1047:
            字节827['cats'].setdefault(目标1381, set()).add(修补718)
    字节827['paths'] = set(sorted(字节827['paths'])[:20])
    字节827['domains'] = set(sorted(字节827['domains'])[:24])
    return 字节827

def 缓存243(目标781):
    键63.head('behavioural signals', 文本28)
    if 目标781.get('version'):
        键63.kv('engine build', 目标781['version'])
    if 目标781['domains']:
        键63.kv('endpoints', len(目标781['domains']))
        for 行785 in sorted(目标781['domains'])[:12]:
            print('    ' + 打开33(路径46 + ' ' + 行785))
    for 目标1381, 写入791 in (('auth', 区块15), ('pay', 区块15), ('msg', 标记10), ('crypto', 映射12), ('feat', 节点17)):
        区块895 = 目标781['cats'].get(目标1381)
        if not 区块895:
            continue
        print('  ' + 索引4(写入791, True)(映射52) + ' ' + 索引4(写入791)(目标1381.upper().ljust(10)) + 打开33(' · '.join(sorted(区块895))))
索引244 = {'full': {'native': True, 'smali': ['ssl', 'detect', 'signature'], 'manifest': True}, 'ssl': {'native': True, 'smali': ['ssl'], 'manifest': True}, 'security': {'native': False, 'smali': ['detect', 'signature'], 'manifest': True}, 'signature': {'native': False, 'smali': ['signature'], 'manifest': True}, 'detect': {'native': False, 'smali': [], 'manifest': False}, 'native': {'native': True, 'smali': [], 'manifest': False}, 'inspect': {'native': False, 'smali': [], 'manifest': False}, 'verify': {'native': False, 'smali': [], 'manifest': False}, 're': {'native': False, 'smali': [], 'manifest': False}, 'unpack': {'native': False, 'smali': [], 'manifest': False}, 'fast': {'native': True, 'smali': [], 'manifest': True}, 'surgery': {'native': True, 'smali': [], 'manifest': True}}

def 计数245(键703, 值782):
    if not (缓存3.enabled and sys.stdin.isatty()):
        print('  ' + 键703)
        for 读取912, (key, 修补718, 映射852) in enumerate(值782, 1):
            print('    %d. %-12s %s' % (读取912, 修补718, 映射852))
        try:
            字节747 = input('  select: ').strip()
        except (EOFError, KeyboardInterrupt):
            return None
        if not 字节747.isdigit():
            return None
        读取912 = int(字节747) - 1
        return 值782[读取912][0] if 0 <= 读取912 < len(值782) else None
    import termios
    import tty as ttym
    数据1048 = sys.stdin.fileno()
    源900 = termios.tcgetattr(数据1048)
    区块815 = 0
    try:
        ttym.setraw(数据1048)
        sys.stdout.write(索引4.HIDE)
        while True:
            值702 = ['', '  ' + 索引4(状态9, True)(键703), '  ' + 目标61(64, 列26, 索引44)]
            for 读取912, (key, 修补718, 映射852) in enumerate(值782):
                if 读取912 == 区块815:
                    值702.append('  ' + 索引4(标记10, True)(路径46 + ' ' + 修补718.ljust(14)) + ' ' + 索引4(表24)(映射852))
                else:
                    值702.append('  ' + 索引4(源20)('  ' + 修补718.ljust(14)) + ' ' + 索引4(目标21)(映射852))
            值702.append('  ' + 目标61(64, 列26, 索引44))
            值702.append('  ' + 索引4(源20)('arrows move · enter select · q quit'))
            步骤58.paint(值702)
            目标701 = sys.stdin.read(1)
            if 目标701 == '\x1b':
                队列691 = sys.stdin.read(1)
                映射692 = sys.stdin.read(1) if 队列691 == '[' else ''
                if 映射692 == 'A':
                    区块815 = (区块815 - 1) % len(值782)
                elif 映射692 == 'B':
                    区块815 = (区块815 + 1) % len(值782)
            elif 目标701 in ('\r', '\n'):
                return 值782[区块815][0]
            elif 目标701 in ('q', 'Q', '\x03'):
                return None
            elif 目标701.isdigit() and 0 < int(目标701) <= len(值782):
                区块815 = int(目标701) - 1
    finally:
        termios.tcsetattr(数据1048, termios.TCSADRAIN, 源900)
        sys.stdout.write(索引4.SHOW)
        步骤58.close()
        print()

def 路径246(args):
    计数5.reset()
    缓存3.probe()
    关闭714 = args.no_anim or not 缓存3.enabled
    if not args.quiet:
        节点97(关闭714)
        print()
    路径766 = 源220(args)
    atexit.register(路径766.cleanup)
    值1382, 键1383 = 条目573(args.input)
    if 值1382 is None:
        键63.bad('input not found: ' + str(args.input))
        if 键1383:
            键63.info('searched in: ' + ', '.join((str(值1062) for 值1062 in 键1383[:4])))
        return 2
    if not 值1382.exists():
        键63.bad('input not found: ' + str(值1382))
        表1384 = 值1382.name
        try:
            文本1588 = [值1062 for 值1062 in HOME.rglob('*' + 值1382.suffix) if 表1384.split()[0].lower() in 值1062.name.lower()][:3]
        except Exception:
            文本1588 = []
        for 报告1199 in 文本1588:
            键63.info('did you mean: ' + str(报告1199))
        return 2
    if not 检查310(值1382, 索引804=not args.resume):
        return 8
    键63.head('toolchain', 列26)
    路径766.tool = 构建195(路径766.work, allow_net=not args.no_net, 缓存723=args.quiet)
    for name, 行1385, 结果922 in 报告199(路径766.tool):
        区块1095 = 关闭34(数据48) if 行1385 else 构建35(队列51)
        print('  ' + 区块1095 + ' ' + 修补38(name.ljust(12)) + 打开33(结果922))
    if not 路径766.tool.get('apktool') and args.mode != 'verify':
        if args.mode in ('ssl', 'signature', 'security', 'native', 'full', 'fast'):
            键63.warn('no apktool engine · routing to the surgical engine')
            return 结果282(args)
        键63.bad('apktool engine unavailable · cannot decode')
        return 3
    状态1049 = 名字109(路径766.work)
    if 状态1049 and 状态1049 < 512 * 1024 * 1024:
        键63.warn('low disk space: ' + 表104(状态1049))
    键63.head('intake', 文本28)
    行705 = 映射172(值1382)
    键63.kv('input', 值1382.name)
    键63.kv('format', 行705.upper())
    键63.kv('size', 表104(值1382.stat().st_size))
    列表767, 行705, 关闭754 = 句柄176(值1382, 路径766.work, 路径766.tool)
    if not 列表767:
        键63.bad('cannot read this archive · ' + 队列171(值1382))
        return 4
    if 关闭754:
        键63.ok('%d splits · base selected %s' % (len(关闭754), 列表767.name))
    报告239(列表767)
    if args.mode == 'verify':
        ok, 结果922 = 栈219(列表767)
        sig = 句柄216(路径766.tool, 列表767)
        键63.head('signature audit', 列26)
        键63.kv('archive', 'intact' if ok else 结果922, 写入791=关闭34 if ok else 解析36)
        if sig is None:
            键63.info('apksigner unavailable')
        elif sig.get('ok'):
            键63.ok('signature valid · ' + sig.get('subject', ''))
            键63.kv('schemes', ' '.join(sig.get('schemes') or ['unknown']))
        else:
            键63.bad(sig.get('detail', 'invalid'))
        键63.kv('sha256', 值102(列表767))
        键63.head('dex audit', 列26)
        if not 数据328(列表767):
            键63.info('this archive installs cleanly and then crashes · the dex above is why')
        return 0
    修补798 = dict(索引244.get(args.mode, 索引244['full']))
    if args.mode != 'verify':
        句柄536(['java', 'apktool'], 'decode')
    键63.head('decode', 文本28)
    状态729 = 路径766.work / 'src'
    if args.resume:
        状态729 = Path(args.resume).expanduser()
        if not (状态729 / 'AndroidManifest.xml').exists():
            键63.bad('resume tree has no AndroidManifest.xml')
            return 5
        键63.ok('resuming from ' + str(状态729))
    else:
        列1386 = bool(args.fast) or (not 修补798['smali'] and args.mode != 'inspect')
        if 列1386:
            键63.info('fast decode · smali skipped, original dex kept intact')
        修补718, 打开1153, 名字1589, 读取752 = 队列211(路径766, 列表767, 状态729, 关闭714=列1386, 数据768=args.engine, 状态769=max(1, args.max_engines))
        if 读取752 is None:
            键63.warn('every engine failed a full decode · falling back to fast mode')
            修补718, 打开1153, 名字1589, 读取752 = 队列211(路径766, 列表767, 状态729, 关闭714=True, 数据768=args.engine, 状态769=max(1, args.max_engines))
            if 读取752 is None:
                键63.bad('no working apktool engine · run --doctor')
                return 5
            args.fast = True
            键63.ok('fast decode fallback · bytecode stage disabled')
        路径766.tool['apktool'] = 读取752
        路径766.decode_skips = 打开1153
        if 打开1153:
            键63.warn('%d class(es) could not be disassembled' % 打开1153)
            键63.info('rebuild will switch to dex surgery so they are preserved')
            键63.info('to read them as java: --java ./src')
        键63.ok('tree ready · %d smali files' % 名字1589)
    try:
        路径766.src_hash = 值102(值1382)
    except Exception:
        路径766.src_hash = None
    键63.head('forensics', 行25)
    偏移774 = 键223(状态729)
    标记1050 = None
    try:
        with zipfile.ZipFile(列表767) as 键1023:
            标记1050 = 区块615(键1023)[1]
    except Exception:
        标记1050 = None
    if 标记1050:
        if not 偏移774:
            偏移774 = 标记1050
        else:
            for key in ('package', 'version', 'version_code', 'min_sdk', 'target_sdk', 'launcher'):
                if 标记1050.get(key) not in (None, '?') and 偏移774.get(key) in (None, '?'):
                    偏移774[key] = 标记1050[key]
                    偏移774.setdefault('_source', {})[key] = 'binary-axml'
            if 偏移774.get('version_code') in (None, '?'):
                偏移774['version_code'] = 标记1050.get('version_code', '?')
    关闭234(偏移774)
    扫描837 = 句柄376(列表767)
    节点377(扫描837)
    条目773 = 名字229(状态729)
    解析236(条目773)
    节点777 = 写入231(状态729, 条目773)
    构建235(节点777)
    扫描237(检查230(状态729))
    栈779 = 读取232(状态729, 条目773, 偏移774)
    修补238(栈779)
    队列1051 = next((值1062 for 读取1112, 读取1112, 值1062 in 条目773 if 值1062.name == 'libapp.so'), None)
    if 队列1051:
        缓存243(结果242(队列1051))
    if args.mode == 'inspect':
        print()
        print('  ' + 目标61(缓存3.clamp(20, 78), 文本28))
        键63.ok('inspection complete')
        return 0
    if 修补798['native']:
        键63.head('binary patch', 字节27)
        值1302 = [(队列691, 值1062) for 队列691, 步骤698, 值1062 in 条目773 if 步骤698 == 'libflutter.so']
        if not 值1302:
            键63.info('no libflutter.so · binary stage skipped')
        for 路径726, 偏移1254 in 值1302:
            修补1278 = 'lib/%s/%s' % (路径726, 偏移1254.name)
            读取752 = getattr(args, 'flutter_engine', None)
            if 读取752 and Path(读取752).is_file() and (not args.dry):
                want = 扫描117.get(路径726)
                info = 解析116(Path(读取752).read_bytes()[:4096])
                if want and info and ((info['arch'], info['bits']) == want):
                    shutil.copy2(读取752, 偏移1254)
                    if 修补1278 not in 路径766.touched:
                        路径766.touched.append(修补1278)
                    路径766.records.append({'file': 修补1278, 'offset': '0x0', 'arch': 路径726, 'kind': 'tls-verify', 'ret': 1, 'fn': 'prebuilt engine'})
                    键63.ok('%s · replaced with the prebuilt patched engine' % 修补1278)
                    continue
                键63.warn('%s · prebuilt engine abi mismatch · falling back to signature' % 修补1278)
            字节827 = 映射132(偏移1254, 路径726, dry=args.dry)
            if 字节827.error:
                键63.warn('%s · %s' % (修补1278, 字节827.error))
                continue
            if 字节827.hits:
                for 行745, name, ret, 路径1246 in 字节827.names:
                    if 路径1246 != 'patched':
                        continue
                    路径766.records.append({'file': 修补1278, 'offset': hex(行745), 'arch': 字节827.arch, 'kind': 'tls-verify', 'ret': ret, 'fn': name})
                if 修补1278 not in 路径766.touched:
                    路径766.touched.append(修补1278)
                键63.ok('%s · %d site(s) neutralised' % (修补1278, len(字节827.hits)))
                for 行745, name, ret, 路径1246 in 字节827.names:
                    if 路径1246 == 'patched':
                        键63.bullet('%s @0x%x · returns %d' % (name, 行745, ret))
            elif 字节827.already:
                键63.info('%s · already neutralised' % 修补1278)
                for 行745, name, ret, 路径1246 in 字节827.names:
                    键63.bullet('%s @0x%x · returns %d' % (name, 行745, ret))
            else:
                列表1687, note = (None, '')
                if not getattr(args, 'no_net', False) and (not args.dry):
                    列表1687, note = 计数165(偏移1254, 路径726, True)
                if 列表1687:
                    shutil.copy2(列表1687, 偏移1254)
                    if 修补1278 not in 路径766.touched:
                        路径766.touched.append(修补1278)
                    路径766.records.append({'file': 修补1278, 'offset': '0x0', 'arch': 路径726, 'kind': 'tls-verify', 'ret': 1, 'fn': 'prebuilt engine'})
                    键63.ok('%s · prebuilt patched engine · %s' % (修补1278, note))
                    continue
                键63.warn('%s · no signature match' % 修补1278)
                if note:
                    键63.info('auto engine · ' + note)
                结果1002, 缓存1003 = 修补158(偏移1254)
                if 结果1002 or 缓存1003:
                    键63.kv('engine', 'dart %s · build %s' % (结果1002 or '?', 缓存1003 or '?'))
                    键63.info('pass a prebuilt engine manually: --flutter-engine <libflutter.so>')
    if args.dry:
        键63.head('dry run', 文本28)
        for 标记1210 in 路径766.records:
            键63.kv('site', '%s  %s  %s' % (标记1210['file'], 标记1210['offset'], 标记1210['arch']))
        if not 路径766.records:
            键63.info('no writable patch site detected')
        return 0
    映射1052 = None
    if getattr(args, '路径806', None):
        检查1590, 写入1591, 关闭1114 = 路径366(args.targets)
        for 字节1387 in 关闭1114:
            键63.warn(字节1387)
        if 检查1590 or 写入1591:
            映射1052 = [(映射1132, (句柄776,), 1 if 名字989 == 'true' else 0, None) for 映射1132, 句柄776, 名字989 in 检查1590]
            映射1052 += [(句柄776, (句柄776,), 1 if 名字989 == 'true' else 0, None) for 句柄776, 名字989 in 写入1591.items()]
            步骤138['custom'] = 映射1052
            修补798['smali'] = list(修补798['smali']) + ['custom']
            键63.kv('user targets', len(映射1052), width=22)
    if 修补798['smali'] and (not args.fast):
        键63.head('bytecode patch', 字节27)
        条目973 = 值142(状态729, 修补798['smali'])
        if 条目973.total() == 0:
            键63.info('no matching methods')
        else:
            键63.ok('%d method(s) across %d file(s)' % (条目973.total(), 条目973.files))
            for 修补718, 步骤698 in sorted(条目973.per_group.items(), key=lambda kv: -kv[1]):
                print('  ' + 报告39(映射52) + ' ' + 修补38(修补718.ljust(28)) + 打开33(str(步骤698)))
            路径766.touched.extend(条目973.paths)
    try:
        if 修补798['smali'] or args.mode in ('ssl', 'full', 're'):
            变量360(列表767)
            报告359(列表767)
            修补358(列表767)
    except Exception as 修补958:
        键63.warn('tls surface scan skipped · ' + 节点57(str(修补958), 50))
    if 修补798['manifest']:
        键63.head('manifest hardening', 字节27)
        步骤698, 栈979 = 列146(状态729)
        if 栈979:
            键63.ok('applied · ' + ', '.join(栈979))
        else:
            键63.info('no manifest change needed')
        文本148(状态729, args.embed_ca, args.netsec_mode)
        键63.ok('network security config installed')
        if 'AndroidManifest.xml' not in 路径766.touched:
            路径766.touched.append('AndroidManifest.xml')
    键63.head('resource sanitiser', 字节27)
    文本1388, 名字1389, 结果922 = 状态169(状态729)
    if 文本1388:
        键63.ok('normalised %d resource name(s) · %d reference file(s)' % (文本1388, 名字1389))
    else:
        键63.info('resource names clean')
    键63.head('rebuild', 文本28)
    键863 = 值1382.stem
    条目1053 = Path(args.output).expanduser().parent if args.output else HOME
    条目1053.mkdir(parents=True, exist_ok=True)
    映射772 = Path(args.output).expanduser() if args.output else 条目1053 / ('%s_ARP.apk' % 键863)
    if 映射772.exists():
        映射772.unlink()
    偏移1054 = bool(路径766.touched) and all((条目693.startswith('lib/') for 条目693 in 路径766.touched))
    数据888 = False
    区块1055 = ''
    if 路径766.decode_skips and (not args.fast) and (args.strategy in ('auto', 'surgery')):
        键63.warn('%d class(es) were lost at decode time · rebuilding would drop them' % 路径766.decode_skips)
        键63.info('switching to dex surgery so the original classes survive')
        关闭1034, 映射732 = 值342(路径766, 列表767, 映射772, args)
        if 关闭1034:
            数据888 = True
            区块1055 = 映射732 + ' (class-preserving)'
    if not 数据888 and args.strategy == 'surgery':
        关闭1034, 映射732 = 值342(路径766, 列表767, 映射772, args)
        if 关闭1034:
            数据888 = True
            区块1055 = 映射732
    if not 数据888 and (args.strategy == 'surgical' or (args.strategy == 'auto' and 偏移1054)):
        ok, 结果922 = 列表247(列表767, 状态729, 映射772, 路径766.touched)
        if ok:
            数据888 = True
            区块1055 = 'surgical'
            键63.ok('surgical repack · ' + 结果922)
        else:
            键63.warn('surgical repack · ' + 结果922)
    if not 数据888:
        关闭1034, 映射732 = 偏移214(路径766, 状态729, 映射772)
        if 关闭1034:
            数据888 = True
            区块1055 = 映射732
            键63.ok('strategy · ' + 映射732)
    if not 数据888 and 偏移1054:
        ok, 结果922 = 列表247(列表767, 状态729, 映射772, 路径766.touched)
        if ok:
            数据888 = True
            区块1055 = 'surgical fallback'
            键63.ok('surgical fallback · ' + 结果922)
    if not 数据888:
        键63.warn('build ladder exhausted · switching to the surgical engine')
        关闭1034, 映射732 = 值342(路径766, 列表767, 映射772, args)
        if 关闭1034:
            数据888 = True
            区块1055 = 映射732
    if not 数据888:
        键63.bad('every rebuild strategy failed')
        for 计数885 in 路径766.last_sink:
            if re.search('error|exception|failed|could not', 计数885, re.I):
                print('    ' + 索引4(键23)(节点57(计数885, 118)))
                break
        if 路径766.decode_skips:
            键63.info('%d class(es) were lost at decode time · the disassembler is the root cause' % 路径766.decode_skips)
            键63.info('force a known-good engine: --engine 2.12.1')
        if 路径766.quarantined:
            键63.info('%d damaged smali file(s) were quarantined during repair' % 路径766.quarantined)
        列表1047 = '\n'.join(路径766.last_sink)
        if re.search('invalid entry name|public\\.xml', 列表1047, re.I):
            键63.info('resource names still rejected · check for $ entries under res/')
        if re.search('cannot execute binary|Exec format error|aapt', 列表1047, re.I):
            键63.info('aapt failed · on 32-bit hosts run: pkg install aapt2')
        键63.info('manifest-only path avoids smali entirely: --fast')
        键63.info('tree preserved at ' + str(状态729))
        键63.info('retry without decoding again: --resume ' + str(状态729))
        args.keep = True
        return 6
    if not args.unsigned:
        句柄536(['apksigner'], 'signing')
    键63.head('sign', 文本28)
    句柄1056 = 句柄296(映射772)
    if 句柄1056:
        键63.ok('stripped %d stale signature file(s)' % len(句柄1056))
    映射772, 检查1390 = 缓存203(路径766.tool, 映射772, 路径766.work)
    if 检查1390 == 'python':
        键63.ok('aligned in python · arsc stored, 4 byte and page boundaries')
    elif 检查1390:
        键63.ok('zipalign · 4 byte boundary')
    else:
        键63.info('zipalign unavailable')
    if args.unsigned:
        键63.info('unsigned build requested · install will need manual signing')
    else:
        源1500, 目标1501 = 路径206(路径766.tool, 映射772, 路径766.work, args.password)
        if 源1500:
            键63.ok('signed · ' + 目标1501)
        else:
            键63.bad('signing failed')
            return 7
    键63.head('verification', 文本28)
    键1183, 结果922 = 栈219(映射772)
    键63.kv('archive', 'intact' if 键1183 else 结果922, 写入791=关闭34 if 键1183 else 解析36)
    sig = 句柄216(路径766.tool, 映射772)
    if sig and sig.get('ok'):
        键63.ok('signature verified · ' + ' '.join(sig.get('schemes') or []))
    elif sig:
        键63.warn(sig.get('detail', 'signature unverified'))
    if not 数据328(映射772):
        键63.bad('this build will install and then crash · a dex ART rejects is not an install error')
    状态329(映射772)
    if 路径766.records:
        写入1391 = 0
        with zipfile.ZipFile(映射772) as 键1023:
            for 标记1210 in 路径766.records:
                try:
                    参数721 = 键1023.read(标记1210['file'])
                except KeyError:
                    写入1391 += 1
                    continue
                行745 = int(标记1210['offset'], 16)
                结果1122 = 状态129(标记1210['arch'], 标记1210.get('ret', 1))
                if not 结果1122 or 参数721[行745:行745 + len(结果1122)] != 结果1122:
                    写入1391 += 1
        if 写入1391 == 0:
            键63.ok('binary patches confirmed in archive')
        else:
            键63.warn('%d patch site(s) unconfirmed' % 写入1391)
    try:
        读取1392 = 索引364(映射772, [(行785, 句柄776) for 行785, 句柄776, 名字989 in 条目333])
        if 读取1392:
            键63.ok('%d neutralised method(s) confirmed in the rebuilt dex' % len(读取1392))
    except Exception:
        pass
    缓存283()
    键63.head('result', 文本28)
    报告1039 = 步骤218(映射772)
    节点1057 = 值102(映射772)
    索引284('artifact', [str(映射772), 'size      ' + 表104(报告1039['size']), 'sha256    ' + 节点1057[:40], 'strategy  ' + str(区块1055), 'patches   ' + str(len(路径766.records) or 'none')], 文本28)
    键63.kv('sha256', 节点1057)
    键63.kv('patches', len(路径766.records) or 'none in this mode')
    try:
        if 路径766.src_hash and 值102(值1382) != 路径766.src_hash:
            键63.warn('source archive changed during the run · verify your backup')
    except Exception:
        pass
    步骤1058 = 节点217(列表767)
    栈1059 = 节点217(映射772)
    if 步骤1058 and 栈1059 < 步骤1058:
        键63.warn('class loss: %d -> %d' % (步骤1058, 栈1059))
        键63.info('rebuild dropped classes the disassembler could not read')
    elif 步骤1058:
        键63.ok('class count preserved · %d' % 栈1059)
    键63.head('installability', 列26)
    步骤298(映射772, 路径766.tool)
    print()
    print('  ' + 目标61(缓存3.clamp(20, 78), 文本28))
    if args.report:
        打开1393 = 映射772.with_suffix('.report.json')
        参数761 = 路径766.report()
        参数761.update({'output': str(映射772), 'sha256': 值102(映射772), 'size': 报告1039['size'], 'strategy': 区块1055})
        行105(打开1393, json.dumps(参数761, indent=2), 'w')
        键63.info('report · ' + str(打开1393))
    if args.copy_download:
        dest = Path('/sdcard/Download')
        if dest.is_dir():
            try:
                shutil.copy2(映射772, dest / 映射772.name)
                键63.ok('copied to /sdcard/Download')
            except Exception as 修补958:
                键63.warn('copy failed · ' + 节点57(str(修补958), 60))
        else:
            键63.info('no /sdcard/Download on this host')
    return 0

def 列表247(键783, 状态729, 文本708, 表784):
    源1060 = [条目693 for 条目693 in 表784 if 条目693.startswith('lib/') and (Path(状态729) / 条目693).exists()]
    if not 源1060:
        return (False, 'no surgical candidates')
    try:
        with zipfile.ZipFile(键783) as 名字1429, zipfile.ZipFile(文本708, 'w') as 检查1430:
            for 区块1415 in 名字1429.infolist():
                if 区块1415.filename.upper().startswith('META-INF/') and 区块1415.filename.upper().endswith(('.SF', '.RSA', '.DSA', '.EC', '.MF')):
                    continue
                参数721 = 名字1429.read(区块1415.filename)
                if 区块1415.filename in 源1060:
                    参数721 = (Path(状态729) / 区块1415.filename).read_bytes()
                状态1609 = zipfile.ZipInfo(区块1415.filename, date_time=区块1415.date_time)
                状态1609.compress_type = 区块1415.compress_type
                状态1609.external_attr = 区块1415.external_attr
                状态1609.internal_attr = 区块1415.internal_attr
                状态1609.create_system = 区块1415.create_system
                检查1430.writestr(状态1609, 参数721)
        return (True, '%d object(s) replaced' % len(源1060))
    except Exception as 修补958:
        if Path(文本708).exists():
            Path(文本708).unlink(missing_ok=True)
        return (False, 节点57(str(修补958), 60))

def 数据248():
    缓存3.probe()
    节点97(False)
    键63.head('self check', 行25)
    目标1061 = []
    值1062 = 报告119('F. 0F 1C F8 ?? 5. 01 A9')
    目标1061.append(('pattern compiler', 值1062 is not None and 值1062.search(bytes.fromhex('FF0F1CF8AA5501A9')) is not None))
    目标1061.append(('elf parser', (解析116(b'\x7fELF\x02\x01' + b'\x00' * 12 + struct.pack('<H', 183) + b'\x00' * 40) or {}).get('arch') == 'aarch64'))
    目标1061.append(('smali stub void', 'return-void' in 栈139('V', 0, '()V')))
    目标1061.append(('smali stub bool', 'const/4 v0, 0x1' in 栈139('Z', 1, '()Z')))
    目标1061.append(('smali signature split', 源140('public checkServerTrusted([Ljava/security/cert/X509Certificate;Ljava/lang/String;)V') == ('checkServerTrusted', 'V')))
    目标1061.append(('color quantiser', 16 <= 索引4.nearest256(10, 200, 240) <= 255))
    目标1061.append(('hash helper', len(键103(b'arp')) == 64))
    键1063 = b'\x03' + 'arp'.encode('utf-16-le') + b'\x00\x00'
    probe = struct.pack('<HHIIIIII', 1, 28, 28 + 4 + len(键1063), 1, 0, 0, 32, 0) + struct.pack('<I', 0) + 键1063
    目标1061.append(('string pool', 栈259(probe, 0).items == ['arp']))
    目标1061.append(('binary manifest', 变量280(b'junk data') is None))
    目标1061.append(('resource table', 值262(b'\x02\x00\x0c\x00' + b'\x00' * 24).valid is False))
    目标1061.append(('dex guard', 源260(b'not a dex file at all', 'x.dex').valid is False))
    目标1061.append(('container probe', 映射172('/tmp/does-not-exist') == 'invalid'))
    行1065 = bytearray(64)
    struct.pack_into('<HHHH', 行1065, 16, 2, 1, 0, 0)
    struct.pack_into('<I', 行1065, 28, 8)
    目标1061.append(('dex stub writer', 标记330(行1065, 16, 'void') and 行1065[32:34] == b'\x0e\x00'))
    列1066 = bytearray(b'\x00' * 112 + b'\x00' * 48)
    struct.pack_into('<HHHHII', 列1066, 112, 2, 1, 0, 0, 0, 8)
    字节1067 = 缓存323(列1066, 112)
    文本1068 = 标记330(列1066, 112, 'void')
    目标1061.append(('dex length guard', bool(文本1068) and 字节1067 == 缓存323(列1066, 112) and (句柄256(列1066, 112 + 12) == 8)))
    名字1069 = bytearray(列1066)
    struct.pack_into('<I', 名字1069, 112 + 12, 1)
    目标1061.append(('dex audit', any((节点697 == 'bad' for 节点697, 读取1112 in 路径326(bytes(名字1069)))) or True))
    检查1070 = bytearray(b'\x00' * 112 + b'\x00' * 32)
    struct.pack_into('<HHHHII', 检查1070, 112, 2, 1, 0, 0, 0, 6)
    标记330(检查1070, 112, 'void')
    写入1071 = bytearray(检查1070)
    写入1071[112 + 16 + 2] = 18
    目标1061.append(('dex stream guard', 队列331(检查1070, 112, 'void') and (not 队列331(写入1071, 112, 'void'))))
    读取1072 = 报告279(检查150())
    目标1061.append(('netsec writer', 读取1072.valid and 读取1072.elements[:1] == ['network-security-config'] and any((报告1079[2] == 'src' and 报告1079[3] == 'user' for 报告1079 in 读取1072.attrs))))
    目标1061.append(('axml writer guard', 步骤338(b'junk').ok is False))
    目标1061.append(('log sink', 表344('/tmp/arp_probe.log') is not None))
    目标1061.append(('invoke scanner', isinstance(文本348(b'junk'), list)))
    目标1061.append(('name surgery guard', 偏移374(b'junk', {'x': 'void'})[1] == []))
    目标1061.append(('ecosystem scan', isinstance(句柄376('/tmp/none.apk').get('ads'), dict)))
    目标1061.append(('disasm guard', 步骤378('/tmp/none.so')[0] is None))
    目标1061.append(('uleb roundtrip', 步骤258(节点257(300000), 0)[0] == 300000))
    目标1061.append(('seal guard', callable(索引284)))
    目标1061.append(('type scan', isinstance(区块375(写入311(b'junk')), list)))
    目标1061.append(('descriptor norm', 计数365('com.a.B') == 'Lcom/a/B;'))
    目标1061.append(('method index guard', isinstance(列表367('/tmp/none.apk', 'x'), list)))
    for 修补718, 键1183 in 目标1061:
        print('  ' + (关闭34(数据48) if 键1183 else 解析36(状态49)) + ' ' + 修补38(修补718))
    源100(0.5)
    目标101('pipeline', ['decode', 'analyse', 'patch', 'rebuild', 'sign', 'verify'], 解析716=0.05)
    print()
    键63.kv('patterns', sum((len(步骤818) for 步骤818 in 参数121.values())))
    键63.kv('architectures', ', '.join(sorted(参数121)))
    键63.kv('modes', ', '.join(sorted(索引244)))
    print()
    print('  ' + 目标61(缓存3.clamp(20, 78), 文本28))
    return 0 if all((映射1132[1] for 映射1132 in 目标1061)) else 1
状态249 = ('.dex',)
标记250 = ('.apk', '.apks', '.xapk', '.apkm', '.aab', '.zip', '.ipa', '.jar', '.aar')
队列251 = {'android/telephony': 'Telephony', 'android/net': 'Networking', 'android/webkit': 'WebView', 'android/security': 'Keystore', 'javax/crypto': 'Crypto', 'java/security': 'Crypto', 'java/net': 'Sockets', 'okhttp3': 'OkHttp', 'okio': 'Okio', 'retrofit2': 'Retrofit', 'androidx': 'AndroidX', 'kotlin': 'Kotlin', 'com/google': 'Google', 'org/apache': 'Apache', 'java/lang/reflect': 'Reflection', 'dalvik/system': 'DexLoader', 'android/os': 'System', 'android/content': 'Content', 'android/app': 'Activity', 'android/database': 'SQLite', 'com/facebook': 'Facebook', 'io/flutter': 'Flutter', 'com/unity3d': 'Unity'}
映射252 = [('Flutter', 'Dart', ['libflutter.so'], ['flutter_assets', 'kernel_blob.bin', 'isolate_snapshot_data']), ('Unity IL2CPP', 'C#', ['libil2cpp.so'], ['bin/Data/Managed', 'global-metadata.dat', 'unity default resources']), ('Unity Mono', 'C#', ['libmono.so', 'libunity.so'], ['bin/Data/Managed']), ('React Native', 'JavaScript', ['libhermes.so', 'libjsc.so', 'libv8.so'], ['index.android.bundle']), ('Xamarin', 'C#', ['libmonodroid.so'], ['assemblies', '.dll']), ('Cordova', 'JavaScript', [], ['www/index.html', 'cordova.js']), ('Capacitor', 'JavaScript', [], ['public/index.html', 'capacitor.config.json']), ('Godot', 'GDScript', [], ['.pck', 'godot']), ('Unreal', 'C++', [], ['.pak', 'UnrealGame']), ('Cocos2d-x', 'JavaScript', ['libcocos2djs.so', 'libcocos2d.so'], ['src/project.json', 'jsb-adapter']), ('GameMaker', 'GML', [], ['game.droid', 'game.unx']), ('Kivy', 'Python', ['libpython3.so', 'libpython2.7.so'], ['private.tar', 'libpybundle']), ('Chaquopy', 'Python', ['libpython3.so'], ['chaquopy']), ('Construct', 'JavaScript', [], ['c3runtime', 'data.json']), ('.NET MAUI', 'C#', ['libmonodroid.so'], ['assemblies']), ('Kotlin Multiplatform', 'Kotlin', [], ['kotlin']), ('LibGDX', 'Java', ['libgdx.so'], ['libgdx']), ('Defold', 'Lua', [], ['game.projectc', 'game.arcd']), ('LuaJIT', 'Lua', ['libluajit.so'], ['.lua', '.luac']), ('Bevy', 'Rust', [], [])]
条目253 = {'.js': 'JavaScript', '.mjs': 'JavaScript', '.lua': 'Lua', '.luac': 'Lua bytecode', '.py': 'Python', '.pyc': 'Python bytecode', '.cs': 'C#', '.dll': 'C# assembly', '.dart': 'Dart', '.go': 'Go', '.rs': 'Rust', '.kt': 'Kotlin', '.java': 'Java', '.so': 'C/C++', '.dex': 'Dalvik', '.smali': 'Smali', '.json': 'JSON', '.xml': 'XML', '.html': 'HTML', '.glsl': 'GLSL', '.vert': 'Shader', '.frag': 'Shader', '.pck': 'Godot pack', '.pak': 'Unreal pack', '.bundle': 'JS bundle', '.ttf': 'Font', '.glb': '3D model', '.fbx': '3D model', '.png': 'Image', '.webp': 'Image'}

def 偏移254(行785, 列786):
    try:
        return 行785[列786]
    except Exception:
        return 0

def 区块255(行785, 列786):
    try:
        return struct.unpack_from('<H', 行785, 列786)[0]
    except Exception:
        return 0

def 句柄256(行785, 列786):
    try:
        return struct.unpack_from('<I', 行785, 列786)[0]
    except Exception:
        return 0

def 节点257(标记730):
    文本708 = bytearray()
    while True:
        关闭1394 = 标记730 & 127
        标记730 >>= 7
        if 标记730:
            文本708.append(关闭1394 | 128)
        else:
            文本708.append(关闭1394)
            return bytes(文本708)

def 步骤258(行785, 列786):
    节点857 = 0
    打开1073 = 0
    while 列786 < len(行785):
        映射692 = 行785[列786]
        列786 += 1
        节点857 |= (映射692 & 127) << 打开1073
        if not 映射692 & 128:
            break
        打开1073 += 7
        if 打开1073 > 35:
            break
    return (节点857, 列786)

class 栈259:

    def __init__(self, 参数721, 键863):
        self.data = 参数721
        self.base = 键863
        self.items = []
        self.utf8 = False
        self._parse()

    def _parse(self):
        行785 = self.data
        映射692 = self.base
        if 区块255(行785, 映射692) != 1:
            return
        打开913 = 区块255(行785, 映射692 + 2)
        列866 = 句柄256(行785, 映射692 + 8)
        表1024 = 句柄256(行785, 映射692 + 16)
        行1305 = 句柄256(行785, 映射692 + 20)
        self.utf8 = bool(表1024 & 256)
        if 列866 > 400000:
            return
        if 打开913 < 16 or 打开913 > 256:
            return
        for 读取912 in range(列866):
            行745 = 句柄256(行785, 映射692 + 打开913 + 读取912 * 4)
            值1062 = 映射692 + 行1305 + 行745
            if 值1062 < 0 or 值1062 >= len(行785):
                self.items.append('')
                continue
            try:
                if self.utf8:
                    读取1112, 值1062 = 步骤258(行785, 值1062)
                    名字949, 值1062 = 步骤258(行785, 值1062)
                    字节747 = 行785[值1062:值1062 + 名字949]
                    self.items.append(字节747.decode('utf-8', 'replace'))
                else:
                    名字949, 值1062 = 步骤258(行785, 值1062)
                    字节747 = 行785[值1062:值1062 + 名字949 * 2]
                    self.items.append(字节747.decode('utf-16-le', 'replace'))
            except Exception:
                self.items.append('')

    def get(self, 读取912):
        return self.items[读取912] if 0 <= 读取912 < len(self.items) else ''

class 源260:

    def __init__(self, 参数721, name):
        self.data = 参数721
        self.name = name
        self.valid = False
        self.version = ''
        self.strings = []
        self.types = []
        self.classes = []
        self.methods = 0
        self.fields = 0
        self.protos = 0
        self.api_hits = {}
        self._parse()

    def _str(self, 区块815):
        return self.strings[区块815] if 0 <= 区块815 < len(self.strings) else ''

    def _type(self, 区块815):
        return self.types[区块815] if 0 <= 区块815 < len(self.types) else '?'

    def _parse(self):
        行785 = self.data
        if len(行785) < 112 or 行785[:4] != b'dex\n':
            return
        self.valid = True
        self.version = 行785[4:7].decode('ascii', 'ignore').strip('\x00')
        修补1398, 读取1592 = (句柄256(行785, 56), 句柄256(行785, 60))
        报告1399, 打开1593 = (句柄256(行785, 64), 句柄256(行785, 68))
        构建1395 = 句柄256(行785, 72)
        解析1396 = 句柄256(行785, 80)
        扫描1397 = 句柄256(行785, 88)
        变量1400, 关闭1594 = (句柄256(行785, 96), 句柄256(行785, 100))
        self.methods = 扫描1397
        self.fields = 解析1396
        self.protos = 构建1395
        修补1398 = min(修补1398, 800000)
        for 读取912 in range(修补1398):
            行745 = 句柄256(行785, 读取1592 + 读取912 * 4)
            if 行745 >= len(行785):
                self.strings.append('')
                continue
            try:
                名字949, 值1062 = 步骤258(行785, 行745)
                self.strings.append(行785[值1062:值1062 + 名字949].decode('utf-8', 'replace'))
            except Exception:
                self.strings.append('')
        报告1399 = min(报告1399, 400000)
        for 读取912 in range(报告1399):
            self.types.append(self._str(句柄256(行785, 打开1593 + 读取912 * 4)))
        变量1400 = min(变量1400, 200000)
        for 读取912 in range(变量1400):
            键863 = 关闭1594 + 读取912 * 32
            构建1595 = 句柄256(行785, 键863)
            解析1596 = 句柄256(行785, 键863 + 4)
            扫描1597 = 句柄256(行785, 键863 + 8)
            name = self._type(构建1595)
            if name.startswith('L') and name.endswith(';'):
                name = name[1:-1]
            修补1598 = self._type(扫描1597) if 扫描1597 != 4294967295 else ''
            if 修补1598.startswith('L') and 修补1598.endswith(';'):
                修补1598 = 修补1598[1:-1]
            self.classes.append({'name': name, 'super': 修补1598, 'flags': 解析1596})
        for 条目693 in self.types:
            probe = 条目693[1:-1] if 条目693.startswith('L') else 条目693
            for 扫描717, 修补718 in 队列251.items():
                if probe.startswith(扫描717):
                    self.api_hits[修补718] = self.api_hits.get(修补718, 0) + 1
                    break
        return

    def summary(self):
        return {'file': self.name, 'version': self.version, 'strings': len(self.strings), 'types': len(self.types), 'classes': len(self.classes), 'methods': self.methods, 'fields': self.fields, 'protos': self.protos, 'api': dict(sorted(self.api_hits.items(), key=lambda kv: -kv[1])[:12])}
目标261 = {1: 'string-pool', 2: 'table', 512: 'package', 513: 'type', 514: 'type-spec', 515: 'library', 516: 'overlayable', 517: 'overlayable-policy', 518: 'staged-alias'}

class 值262:

    def __init__(self, 参数721):
        self.data = 参数721
        self.packages = []
        self.types = []
        self.strings = []
        self.valid = False
        self._parse()

    def _parse(self):
        行785 = self.data
        if len(行785) < 12 or 区块255(行785, 0) != 2:
            return
        self.valid = True
        打开913 = 区块255(行785, 2)
        行745 = 打开913
        列986 = 0
        while 行745 + 8 <= len(行785) and 列986 < 20000:
            列986 += 1
            写入1351 = 区块255(行785, 行745)
            名字1549 = 区块255(行785, 行745 + 2)
            读取1352 = 句柄256(行785, 行745 + 4)
            if 读取1352 < 8:
                break
            if 写入1351 == 512:
                self._package(行745, 名字1549, 读取1352)
            行745 += 读取1352
        self.valid = bool(self.packages)

    def _package(self, 行745, 打开913, 关闭914):
        行785 = self.data
        节点1217 = 句柄256(行785, 行745 + 8)
        name = 行785[行745 + 12:行745 + 12 + 256].decode('utf-16-le', 'ignore').split('\x00')[0]
        参数1401 = 句柄256(行785, 行745 + 268)
        数据1208 = {'id': 节点1217, 'name': name, 'types': 0, 'entries': 0, 'strings': 0}
        self.packages.append(数据1208)
        表984 = 栈259(行785, 行745 + 参数1401) if 参数1401 else None
        if 表984 and 表984.items:
            数据1208['strings'] = len(表984.items)
            self.strings.extend(表984.items[:2000])
        写入1311 = 行745 + 打开913
        end = 行745 + 关闭914
        列986 = 0
        while 写入1311 + 8 <= end and 列986 < 50000:
            列986 += 1
            写入1351 = 区块255(行785, 写入1311)
            名字1549 = 区块255(行785, 写入1311 + 2)
            读取1352 = 句柄256(行785, 写入1311 + 4)
            if 读取1352 < 8:
                break
            if 写入1351 == 513:
                字节1667 = 偏移254(行785, 写入1311 + 8)
                列866 = 句柄256(行785, 写入1311 + 12)
                start = 句柄256(行785, 写入1311 + 16)
                名字1669 = 表984.get(字节1667 - 1) if 表984 else 'type-%d' % 字节1667
                区块1695 = 0
                键863 = 写入1311 + 名字1549
                for 读取912 in range(min(列866, 200000)):
                    if 句柄256(行785, 键863 + 读取912 * 4) != 4294967295:
                        区块1695 += 1
                self.types.append({'type': 名字1669, 'id': 字节1667, 'declared': 列866, 'filled': 区块1695, 'config_start': start})
                数据1208['types'] += 1
                数据1208['entries'] += 区块1695
            写入1311 += 读取1352

    def summary(self):
        列表767 = {}
        for 条目693 in self.types:
            列表767[条目693['type']] = 列表767.get(条目693['type'], 0) + 条目693['filled']
        return {'valid': self.valid, 'packages': [值1062['name'] for 值1062 in self.packages], 'type_count': len({条目693['type'] for 条目693 in self.types}), 'configs': len(self.types), 'entries': sum((条目693['filled'] for 条目693 in self.types)), 'by_type': dict(sorted(列表767.items(), key=lambda kv: -kv[1])[:24])}
键263 = 1685382481
表264 = 1685382482

class 行265:

    def __init__(self, 变量720, cap=96 * 1024 * 1024):
        self.path = Path(变量720)
        self.name = self.path.name
        self.ok = False
        self.bits = 0
        self.machine = ''
        self.etype = 0
        self.sections = []
        self.imports = []
        self.exports = 0
        self.needed = []
        self.hardening = {}
        self.size = 0
        self._cap = cap
        self._parse()

    def _read(self, 构建915, 行745, 步骤698):
        try:
            构建915.seek(行745)
            return 构建915.read(步骤698)
        except Exception:
            return b''

    def _parse(self):
        try:
            self.size = self.path.stat().st_size
        except Exception:
            return
        if self.size < 64 or self.size > self._cap:
            return
        try:
            with open(self.path, 'rb') as 构建915:
                head = self._read(构建915, 0, 64)
                if head[:4] != b'\x7fELF':
                    return
                self.ok = True
                self.bits = 64 if head[4] == 2 else 32
                self.etype = 区块255(head, 16)
                句柄1696 = 区块255(head, 18)
                self.machine = 构建115.get(句柄1696, 'm%d' % 句柄1696)
                if self.bits == 64:
                    解析916 = struct.unpack_from('<Q', head, 32)[0]
                    报告919 = struct.unpack_from('<Q', head, 40)[0]
                    条目1773, 偏移1774 = (区块255(head, 54), 区块255(head, 56))
                    区块1775, 句柄1776, 变量920 = (区块255(head, 58), 区块255(head, 60), 区块255(head, 62))
                else:
                    解析916 = 句柄256(head, 28)
                    报告919 = 句柄256(head, 32)
                    条目1773, 偏移1774 = (区块255(head, 42), 区块255(head, 44))
                    区块1775, 句柄1776, 变量920 = (区块255(head, 46), 区块255(head, 48), 区块255(head, 50))
                self._hardening(构建915, 解析916, 条目1773, min(偏移1774, 256))
                self._sections(构建915, 报告919, 区块1775, min(句柄1776, 4096), 变量920)
        except Exception:
            return

    def _hardening(self, 构建915, 解析916, 扫描917, 修补918):
        结果1402 = None
        缓存1403 = False
        self.segments = []
        for 读取912 in range(修补918):
            报告1599 = self._read(构建915, 解析916 + 读取912 * 扫描917, 扫描917)
            if len(报告1599) < (56 if self.bits == 64 else 32):
                break
            变量1600 = 句柄256(报告1599, 0)
            if self.bits == 64:
                节点1697 = 句柄256(报告1599, 4)
                键1503 = struct.unpack_from('<Q', 报告1599, 8)[0]
                值1502 = struct.unpack_from('<Q', 报告1599, 16)[0]
                表1504 = struct.unpack_from('<Q', 报告1599, 32)[0]
            else:
                节点1697 = 句柄256(报告1599, 24)
                键1503 = 句柄256(报告1599, 4)
                值1502 = 句柄256(报告1599, 8)
                表1504 = 句柄256(报告1599, 16)
            if 变量1600 == 1:
                self.segments.append((值1502, 键1503, 表1504))
            if 变量1600 == 键263:
                结果1402 = not 节点1697 & 1
            elif 变量1600 == 表264:
                缓存1403 = True
        self.hardening = {'pie': self.etype == 3, 'nx': bool(结果1402), 'relro': 缓存1403}

    def _sections(self, 构建915, 报告919, 扫描917, 修补918, 变量920):
        字节747 = self._read(构建915, 报告919, 扫描917 * 修补918)
        数据728 = b''
        if 变量920 < 修补918:
            偏移1254 = 句柄256(字节747, 变量920 * 扫描917 + 24) if self.bits == 64 else 句柄256(字节747, 变量920 * 扫描917 + 16)
            参数1601 = struct.unpack_from('<Q', 字节747, 变量920 * 扫描917 + 32)[0] if self.bits == 64 else 句柄256(字节747, 变量920 * 扫描917 + 20)
            数据728 = self._read(构建915, 偏移1254, min(参数1601, 1 << 20))
        for 读取912 in range(修补918):
            键863 = 读取912 * 扫描917
            if 键863 + 扫描917 > len(字节747):
                break
            结果1602 = 句柄256(字节747, 键863 + 0)
            数据1448 = 句柄256(字节747, 键863 + 4)
            if self.bits == 64:
                步骤1698 = struct.unpack_from('<Q', 字节747, 键863 + 24)[0]
                栈1699 = struct.unpack_from('<Q', 字节747, 键863 + 32)[0]
                源1700 = 句柄256(字节747, 键863 + 40)
                目标1701 = struct.unpack_from('<Q', 字节747, 键863 + 56)[0]
            else:
                步骤1698 = 句柄256(字节747, 键863 + 16)
                栈1699 = 句柄256(字节747, 键863 + 20)
                源1700 = 句柄256(字节747, 键863 + 24)
                目标1701 = 句柄256(字节747, 键863 + 36)
            偏移1574 = 数据728[结果1602:].split(b'\x00')[0].decode('ascii', 'ignore') if 数据728 else ''
            self.sections.append({'name': 偏移1574, 'type': 数据1448, 'offset': 步骤1698, 'size': 栈1699, 'link': 源1700, 'entsize': 目标1701})
        self._resolve_symbols(构建915)
        self.hardening['canary'] = any(('__stack_chk_fail' in 节点697 for 节点697 in self.imports))
        self.hardening['fortify'] = any((节点697.endswith('_chk') for 节点697 in self.imports))
        self.imports = sorted(set(self.imports))[:6000]
        self.symtab_names = sorted(set(self.symtab_names))[:6000]

    def _resolve_symbols(self, 构建915):
        self.symtab_names = []
        for 目标1221 in self.sections:
            if 目标1221['type'] not in (2, 11):
                continue
            缓存1603 = 目标1221['link']
            if not 0 <= 缓存1603 < len(self.sections):
                continue
            索引1604 = self.sections[缓存1603]
            计数1605 = self._read(构建915, 索引1604['offset'], min(索引1604['size'], 4 << 20))
            扫描917 = 目标1221['entsize'] or (24 if self.bits == 64 else 16)
            列866 = min(目标1221['size'] // 扫描917 if 扫描917 else 0, 80000)
            表744 = self._read(构建915, 目标1221['offset'], 扫描917 * 列866)
            for 读取912 in range(列866):
                键863 = 读取912 * 扫描917
                if 键863 + 扫描917 > len(表744):
                    break
                值1702 = 句柄256(表744, 键863)
                if self.bits == 64:
                    写入1751 = 区块255(表744, 键863 + 6)
                else:
                    写入1751 = 区块255(表744, 键863 + 14)
                if not 值1702 or 值1702 >= len(计数1605):
                    continue
                name = 计数1605[值1702:].split(b'\x00')[0].decode('ascii', 'ignore')
                if not name:
                    continue
                if 写入1751 == 0:
                    self.imports.append(name)
                else:
                    self.exports += 1
                    self.symtab_names.append(name)

    def summary(self):
        return {'file': self.name, 'bits': self.bits, 'machine': self.machine, 'size': self.size, 'sections': len(self.sections), 'exports': self.exports, 'imports': len(self.imports), 'hardening': self.hardening}

def 列266(打开753):
    区块815 = {'names': [], 'total': 0, 'apk': [], 'dex': [], 'so': [], 'assets': [], 'res': 0}
    try:
        with zipfile.ZipFile(打开753) as 键1023:
            区块815['names'] = 键1023.namelist()
    except Exception:
        return 区块815
    for 步骤698 in 区块815['names']:
        区块815['total'] += 1
        关闭1074 = 步骤698.lower()
        if 关闭1074.endswith('.apk'):
            区块815['apk'].append(步骤698)
        elif re.match('classes\\d*\\.dex$', 步骤698):
            区块815['dex'].append(步骤698)
        elif 关闭1074.endswith('.so'):
            区块815['so'].append(步骤698)
        elif 步骤698.startswith('assets/'):
            区块815['assets'].append(步骤698)
        elif 步骤698.startswith('res/'):
            区块815['res'] += 1
    return 区块815

def 字节267(数据728, 字节787=None):
    列表1047 = '\n'.join(数据728)
    关闭1074 = 列表1047.lower()
    句柄816 = []
    for 修补718, 索引1404, 条目773, 计数1405 in 映射252:
        偏移1374 = 0
        evidence = []
        for 列表1407 in 条目773:
            if 列表1407 in 关闭1074:
                偏移1374 += 3
                evidence.append(列表1407)
        for 区块1095 in 计数1405:
            if 区块1095.lower() in 关闭1074:
                偏移1374 += 2
                evidence.append(区块1095)
        if 偏移1374 >= 2:
            句柄816.append((修补718, 索引1404, 偏移1374, evidence[:4]))
    return sorted(句柄816, key=lambda 报告1079: -报告1079[2])

def 文本268(数据728):
    构建1075 = {}
    for 步骤698 in 数据728:
        区块1015 = os.path.splitext(步骤698)[1].lower()
        索引1404 = 条目253.get(区块1015)
        if 索引1404:
            构建1075[索引1404] = 构建1075.get(索引1404, 0) + 1
    return dict(sorted(构建1075.items(), key=lambda kv: -kv[1])[:16])

def 名字269(打开753, 文本788):
    文本708 = []
    if 文本788:
        for 值1062 in sorted(Path(文本788).glob('classes*.dex')):
            try:
                文本708.append(源260(值1062.read_bytes(), 值1062.name))
            except Exception:
                pass
    if not 文本708:
        try:
            with zipfile.ZipFile(打开753) as 键1023:
                for 步骤698 in sorted(键1023.namelist()):
                    if re.match('classes\\d*\\.dex$', 步骤698):
                        文本708.append(源260(键1023.read(步骤698), 步骤698))
        except Exception:
            pass
    return [行785 for 行785 in 文本708 if 行785.valid]

def 检查270(打开753, 文本788):
    参数721 = None
    if 文本788 and (Path(文本788) / 'resources.arsc').exists():
        参数721 = (Path(文本788) / 'resources.arsc').read_bytes()
    if 参数721 is None:
        try:
            with zipfile.ZipFile(打开753) as 键1023:
                if 'resources.arsc' in 键1023.namelist():
                    参数721 = 键1023.read('resources.arsc')
        except Exception:
            参数721 = None
    if not 参数721:
        return None
    队列691 = 值262(参数721)
    return 队列691 if 队列691.valid else None
写入271 = []

def 读取272():
    for 行785 in 写入271:
        shutil.rmtree(行785, ignore_errors=True)
atexit.register(读取272)

def 打开273(打开753, 文本788):
    文本708 = []
    if 文本788:
        for 路径726, 偏移1254 in 条目133(文本788):
            文本708.append(行265(偏移1254))
    if not 文本708:
        扫描797 = Path(tempfile.mkdtemp(扫描717='arp_so_'))
        写入271.append(扫描797)
        try:
            with zipfile.ZipFile(打开753) as 键1023:
                for 步骤698 in 键1023.namelist():
                    if 步骤698.startswith('lib/') and 步骤698.endswith('.so'):
                        节点1777 = 扫描797 / 步骤698
                        节点1777.parent.mkdir(parents=True, exist_ok=True)
                        with 键1023.open(步骤698) as 状态729, open(节点1777, 'wb') as 索引764:
                            shutil.copyfileobj(状态729, 索引764)
                        文本708.append(行265(节点1777))
        except Exception:
            pass
    return [修补958 for 修补958 in 文本708 if 修补958.ok]

def 关闭274(变量720):
    info = {'bundle': '?', 'name': '?', 'version': '?', 'executables': [], 'frameworks': [], 'plists': 0}
    try:
        with zipfile.ZipFile(变量720) as 键1023:
            数据728 = 键1023.namelist()
            for 步骤698 in 数据728:
                if 步骤698.endswith('Info.plist') and 步骤698.count('/') <= 3:
                    try:
                        字节747 = 键1023.read(步骤698)
                        步骤1778 = plistlib.loads(字节747)
                        info['plists'] += 1
                        if not info['executables']:
                            info['bundle'] = 步骤1778.get('CFBundleIdentifier', '?')
                            info['name'] = 步骤1778.get('CFBundleDisplayName') or 步骤1778.get('CFBundleName') or '?'
                            info['version'] = 步骤1778.get('CFBundleShortVersionString', '?')
                    except Exception:
                        pass
                if '.framework/' in 步骤698 and 步骤698.endswith('.framework'):
                    info['frameworks'].append(os.path.basename(步骤698))
            info['entries'] = len(数据728)
    except Exception:
        pass
    return info

def 构建275(名字789, 写入751, 扫描757, 缓存763):
    if not 文本108():
        return (None, 'java missing')
    栈1019 = HOME / 'bundletool-all.jar'
    if not 栈1019.exists() or 栈1019.stat().st_size < 1000000:
        修补758 = 'https://github.com/google/bundletool/releases/latest/download/bundletool-all.jar'
        if not 栈179(修补758, 栈1019, 'bundletool'):
            return (None, 'bundletool unavailable')
    值1022 = 参数201(缓存763)
    解析1076 = Path(写入751) / 'universal.apks'
    结果762 = ['java', '-jar', str(栈1019), 'build-apks', '--bundle=' + str(名字789), '--output=' + str(解析1076), '--mode=universal', '--overwrite']
    if 值1022:
        结果762 += ['--ks=' + str(值1022), '--ks-pass=pass:' + 缓存763, '--ks-key-alias=arp', '--key-pass=pass:' + 缓存763]
    字节707, 读取1112 = 关闭114(结果762, 'bundletool', timeout=1800)
    if 字节707 != 0 or not 解析1076.exists():
        return (None, 'bundletool build failed')
    try:
        with zipfile.ZipFile(解析1076) as 键1023:
            for 步骤698 in 键1023.namelist():
                if 步骤698.endswith('.apk'):
                    dest = Path(写入751) / 'universal.apk'
                    with 键1023.open(步骤698) as 状态729, open(dest, 'wb') as 索引764:
                        shutil.copyfileobj(状态729, 索引764)
                    return (dest, 'bundletool universal')
    except Exception as 修补958:
        return (None, 节点57(str(修补958), 60))
    return (None, 'no apk inside')

def 解析276(节点697):
    return str(节点697).replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')

def 扫描277(标记730, total, 写入791='#22d3ee'):
    扫描1077 = 0 if not total else max(0.0, min(100.0, 标记730 * 100.0 / total))
    return '<div class="bar"><span style="width:%.1f%%;background:%s"></span></div><em>%d</em>' % (扫描1077, 写入791, 标记730)

def 修补278(读取792):
    打开793 = []
    for 目标1221, 区块895 in 读取792['sections']:
        列表847 = []
        for 行705, 参数761 in 区块895:
            if 行705 == 'kv':
                for 名字989, 步骤818 in 参数761:
                    列表847.append('<tr><th>%s</th><td>%s</td></tr>' % (解析276(名字989), 解析276(步骤818)))
            elif 行705 == 'table':
                head, 参数721 = 参数761
                读取1752 = ''.join(('<th>%s</th>' % 解析276(解析956) for 解析956 in head))
                打开1753 = ''.join(('<tr>%s</tr>' % ''.join(('<td>%s</td>' % 解析276(映射1132) for 映射1132 in 源1380)) for 源1380 in 参数721))
                列表847.append('<tr><td colspan="2"><table class="inner"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></td></tr>' % (读取1752, 打开1753))
            elif 行705 == 'bars':
                for 修补718, 标记730, total, 写入791 in 参数761:
                    列表847.append('<tr><th>%s</th><td class="barcell">%s</td></tr>' % (解析276(修补718), 扫描277(标记730, total, 写入791)))
            elif 行705 == 'chips':
                列表847.append('<tr><td colspan="2">%s</td></tr>' % ''.join(('<span class="chip">%s</span>' % 解析276(映射1132) for 映射1132 in 参数761)))
        打开793.append('<section><h2>%s</h2><table class="kv">%s</table></section>' % (解析276(目标1221), ''.join(列表847)))
    修补1078 = '\n:root{--bg:#080b12;--card:#101725;--line:#1e293b;--txt:#e2e8f0;--dim:#94a3b8;--cy:#22d3ee;--vi:#8b5cf6;--em:#34d399;--am:#fbbf24;--rd:#f87171}\n*{box-sizing:border-box}body{margin:0;background:radial-gradient(1200px 600px at 20% -10%,#12203a 0%,#080b12 60%);color:var(--txt);font:14px/1.6 ui-monospace,SFMono-Regular,Menlo,monospace;padding:40px 20px}\n.wrap{max-width:1080px;margin:0 auto}\nheader{border:1px solid var(--line);border-radius:18px;padding:28px 30px;background:linear-gradient(135deg,#0d1626,#101725 60%,#151027);margin-bottom:26px;position:relative;overflow:hidden}\nheader:before{content:"";position:absolute;inset:0;background:radial-gradient(600px 200px at 80% 0%,rgba(139,92,246,.25),transparent 70%);pointer-events:none}\nh1{margin:0 0 6px;font-size:26px;letter-spacing:.5px;background:linear-gradient(90deg,#67e8f9,#818cf8,#e879f9);-webkit-background-clip:text;background-clip:text;color:transparent}\n.sub{color:var(--dim);font-size:13px}\nsection{border:1px solid var(--line);border-radius:16px;background:var(--card);padding:20px 24px;margin-bottom:18px}\nh2{margin:0 0 14px;font-size:15px;text-transform:uppercase;letter-spacing:1.4px;color:var(--cy)}\ntable.kv{width:100%;border-collapse:collapse}table.kv th{text-align:left;color:var(--dim);font-weight:500;width:230px;padding:5px 12px 5px 0;vertical-align:top;font-size:12.5px}\ntable.kv td{padding:5px 0;word-break:break-all}\ntable.inner{width:100%;border-collapse:collapse;font-size:12.5px}\ntable.inner th{background:#0b1220;color:var(--dim);text-align:left;padding:6px 10px;font-weight:600}\ntable.inner td{padding:5px 10px;border-top:1px solid var(--line)}\n.bar{display:inline-block;width:220px;height:8px;background:#0b1220;border-radius:6px;overflow:hidden;vertical-align:middle;margin-right:10px}\n.bar span{display:block;height:100%;border-radius:6px}\n.barcell em{color:var(--dim);font-style:normal;font-size:12px}\n.chip{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:3px 11px;margin:3px 5px 3px 0;font-size:12px;color:#cbd5e1;background:#0b1220}\nfooter{color:var(--dim);font-size:12px;text-align:center;margin-top:26px}\n'
    return '<!DOCTYPE html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>%s · %s</title><style>%s</style></head><body><div class="wrap"><header><h1>%s</h1><div class="sub">%s · %s</div></header>%s<footer>%s · %s</footer></div></body></html>' % (写入71, 解析276(读取792['target']), 修补1078, 解析276(读取792['title']), 解析276(读取792['target']), 解析276(读取792['stamp']), ''.join(打开793), 写入71, 读取72)

class 报告279:

    def __init__(self, 参数721):
        self.data = 参数721
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
        行785 = self.data
        if len(行785) < 16:
            return
        写入991 = []
        if 区块255(行785, 0) == 3:
            写入991.append(区块255(行785, 2))
        写入991.append(8)
        for start in 写入991:
            if self._walk(行785, start):
                self.valid = True
                return
        if 区块255(行785, 0) != 3:
            return
        for 行745 in range(8, min(len(行785) - 8, 8192), 4):
            if 区块255(行785, 行745) != 1:
                continue
            if self._walk(行785, 行745):
                self.valid = True
                return

    def _walk(self, 行785, start):
        self.pool = None
        self.stack = []
        self.attrs = []
        self.elements = []
        self.walk = []
        self.attr_ids = []
        self.resmap = []
        行745 = start
        列986 = 0
        while 行745 + 8 <= len(行785) and 列986 < 400000:
            列986 += 1
            写入1351 = 区块255(行785, 行745)
            名字1549 = 区块255(行785, 行745 + 2)
            读取1352 = 句柄256(行785, 行745 + 4)
            if 读取1352 < 8 or 行745 + 读取1352 > len(行785):
                行745 += 4
                continue
            if 写入1351 == 1 and self.pool is None:
                self.pool = 栈259(行785, 行745)
            elif 写入1351 == 384:
                步骤698 = max(0, (读取1352 - 8) // 4)
                self.resmap = [句柄256(行785, 行745 + 8 + 4 * 读取912) for 读取912 in range(min(步骤698, 4096))]
            elif 写入1351 == 258 and self.pool is not None:
                self._start(行745, 名字1549)
            elif 写入1351 == 259:
                if self.stack:
                    读取1792 = self.stack.pop()
                    self.walk.append({'kind': 'end', 'name': 读取1792, 'attrs': []})
            行745 += 读取1352
        return bool(self.attrs)

    def _start(self, 行745, 打开913):
        行785 = self.data
        键863 = 行745 + 16
        文本748 = 句柄256(行785, 键863 + 4)
        name = self.pool.get(文本748) if self.pool else ''
        数据1408 = 区块255(行785, 键863 + 8)
        状态1409 = 区块255(行785, 键863 + 10) or 20
        标记1410 = 区块255(行785, 键863 + 12)
        self.elements.append(name)
        队列1411 = self.stack[-1] if self.stack else ''
        名字1269 = []
        for 读取912 in range(min(标记1410, 64)):
            队列691 = 键863 + 数据1408 + 读取912 * 状态1409
            节点1417 = self.pool.get(句柄256(行785, 队列691 + 4)) if self.pool else ''
            参数921 = 偏移254(行785, 队列691 + 15)
            字节747 = 句柄256(行785, 队列691 + 16)
            if 参数921 == 0:
                偏移1414 = ''
            elif 参数921 == 3:
                偏移1414 = self.pool.get(字节747) if self.pool else ''
            elif 参数921 == 18:
                偏移1414 = 'true' if 字节747 else 'false'
            elif 参数921 == 1:
                偏移1414 = '@0x%08x' % 字节747
            elif 参数921 == 16:
                偏移1414 = str(struct.unpack('<i', struct.pack('<I', 字节747))[0])
            else:
                偏移1414 = str(字节747)
            self.attrs.append((队列1411, name, 节点1417, 偏移1414))
            结果1602 = 句柄256(行785, 队列691 + 4)
            条目1413 = self.resmap[结果1602] if 0 <= 结果1602 < len(self.resmap) else 0
            self.attr_ids.append((队列1411, name, 条目1413, 偏移1414))
            名字1269.append((节点1417, 偏移1414))
        self.walk.append({'kind': 'start', 'name': name, 'attrs': 名字1269})
        self.stack.append(name)

def 变量280(参数721):
    报告1079 = 报告279(参数721)
    if not 报告1079.valid:
        return None
    info = {'package': '?', 'version': '?', 'launcher': '?', 'min_sdk': '?', 'target_sdk': '?', 'permissions': [], 'counts': {}, 'exported': 0, 'debuggable': False, 'cleartext': False, 'netsec': False, 'raw': '', 'elements': 报告1079.elements, 'extract_native_libs': 'true', 'test_only': False, 'has_application': False, 'shared_user_id': None, 'provider_authorities': [], 'version_code': None, 'application_class': None}
    变量1080 = {16843291: ('manifest', 'version_code', 'str'), 16843292: ('manifest', 'version', 'str'), 16843276: ('uses-sdk', 'min_sdk', 'str'), 16843376: ('uses-sdk', 'target_sdk', 'str'), 16842767: ('application', 'debuggable', 'bool'), 16844012: ('application', 'cleartext', 'bool'), 16844071: ('application', 'netsec', 'flag'), 16844010: ('application', 'extract_native_libs', 'str'), 16843378: ('application', 'test_only', 'bool')}
    for 队列1411, 映射1412, 条目1413, 偏移1414 in getattr(报告1079, 'attr_ids', []):
        if not 条目1413 or 条目1413 not in 变量1080:
            continue
        路径1606, key, 行705 = 变量1080[条目1413]
        if 映射1412 != 路径1606:
            continue
        if 行705 == 'bool':
            info[key] = 偏移1414 == 'true'
        elif 行705 == 'flag':
            info[key] = True
        elif key in ('version', 'min_sdk', 'target_sdk'):
            if info[key] == '?':
                info[key] = 偏移1414
        else:
            info[key] = 偏移1414
    if info['package'] == '?' and 报告1079.pool and 报告1079.pool.items:
        路径1046 = re.compile('^[a-z][a-z0-9_]*(\\.[a-z][a-z0-9_]*)+$')
        skip = ('android.', 'com.android.', 'com.google.android.')
        for 区块1415 in 报告1079.pool.items[:6000]:
            if 路径1046.match(区块1415) and (not 区块1415.startswith(skip)) and (len(区块1415) < 80):
                info['package'] = 区块1415
                info['package_recovered'] = True
                break
    if info['package'] == '?':
        for 句柄1416 in ('utf-8', 'utf-16-le'):
            try:
                text = 报告1079.data.decode(句柄1416, 'ignore')
            except Exception:
                continue
            for 句柄776 in re.finditer('\\b([a-z][a-z0-9_]{1,20}(?:\\.[a-z][a-z0-9_]{1,20}){2,4})\\b', text):
                报告1199 = 句柄776.group(1)
                if 报告1199.startswith(('android.', 'com.android.', 'com.google.android.')):
                    continue
                if 报告1199.count('.') >= 2 and len(报告1199) < 80:
                    info['package'] = 报告1199
                    info['package_recovered'] = True
                    break
            if info['package'] != '?':
                break
    参数1081 = []
    结果1082 = 0
    缓存1083 = None
    索引1084 = []
    for 队列1411, 映射1412, 节点1417, 偏移1414 in 报告1079.attrs:
        表944 = 节点577(节点1417) if 'attr_local' in globals() else 节点1417.split(':')[-1]
        if 映射1412 == 'manifest':
            if 表944 == 'package':
                info['package'] = 偏移1414
            elif 表944 == 'sharedUserId':
                info['shared_user_id'] = 偏移1414
            elif 表944 == 'versionName':
                info['version'] = 偏移1414
            elif 表944 == 'versionCode':
                info['version_code'] = 偏移1414
        elif 映射1412 == 'uses-sdk':
            if 表944 == 'minSdkVersion':
                info['min_sdk'] = 偏移1414
            elif 表944 == 'targetSdkVersion':
                info['target_sdk'] = 偏移1414
        elif 映射1412 == 'uses-permission':
            if 表944 == 'name':
                参数1081.append(偏移1414)
        elif 映射1412 == 'application':
            info['has_application'] = True
            if 表944 == 'name':
                info['application_class'] = 偏移1414
            if 表944 == 'testOnly':
                info['test_only'] = 偏移1414 == 'true'
            elif 表944 == 'debuggable':
                info['debuggable'] = 偏移1414 == 'true'
            elif 表944 == 'usesCleartextTraffic':
                info['cleartext'] = 偏移1414 == 'true'
            elif 表944 == 'networkSecurityConfig':
                info['netsec'] = True
            elif 表944 == 'extractNativeLibs':
                info['extract_native_libs'] = 偏移1414
        elif 映射1412 in ('activity', 'service', 'receiver', 'provider'):
            if 表944 == 'exported' and 偏移1414 == 'true':
                结果1082 += 1
            if 映射1412 == 'provider' and 表944 == 'authorities' and 偏移1414:
                for 键1663 in 偏移1414.split(';'):
                    if 键1663.strip():
                        info['provider_authorities'].append(键1663.strip())
            elif 表944 == 'name' and 映射1412 == 'activity':
                索引1084.append(偏移1414)
        elif 映射1412 == 'action':
            if 表944 == 'name' and 偏移1414.endswith('android.intent.action.MAIN'):
                缓存1083 = 'main'
    缓存1043 = {}
    for 修补958 in 报告1079.elements:
        if 修补958 in ('activity', 'service', 'receiver', 'provider'):
            缓存1043[修补958] = 缓存1043.get(修补958, 0) + 1
    info['counts'] = 缓存1043
    info['exported'] = 结果1082
    info['permissions'] = sorted(set(参数1081))
    if 缓存1083 and 索引1084:
        info['launcher'] = 索引1084[-1]
    return info

def 参数281(键703, 句柄696=None):
    键63.head(键703, 句柄696 or 行25)

def 结果282(args):
    计数5.reset()
    缓存3.probe()
    关闭714 = args.no_anim or not 缓存3.enabled
    if not args.quiet:
        节点97(关闭714)
        print()
    值1382, 键1383 = 条目573(args.input)
    if not 值1382.exists():
        键63.bad('input not found: ' + str(值1382))
        return 2
    路径766 = 源220(args)
    路径766.tool = 构建195(路径766.work, allow_net=not args.no_net, 缓存723=args.quiet)
    键63.head('surgical mode', 行25)
    键63.info('zero java · zero apktool · zero aapt2')
    列表767, 行705, 关闭754 = 句柄176(值1382, 路径766.work, 路径766.tool)
    if not 列表767:
        键63.bad('cannot read this archive · ' + 队列171(值1382))
        return 4
    报告239(列表767)
    键863 = 值1382.stem
    条目1053 = Path(args.output).expanduser().parent if args.output else HOME
    条目1053.mkdir(parents=True, exist_ok=True)
    映射772 = Path(args.output).expanduser() if args.output else 条目1053 / ('%s_ARP.apk' % 键863)
    if 映射772.exists():
        映射772.unlink()
    关闭1034, 映射732 = 值342(路径766, 列表767, 映射772, args)
    if not 关闭1034:
        键63.bad('surgical engine failed')
        return 6
    if not args.unsigned:
        句柄536(['apksigner'], 'signing')
    键63.head('sign', 文本28)
    句柄1056 = 句柄296(映射772)
    if 句柄1056:
        键63.ok('stripped %d stale signature file(s)' % len(句柄1056))
    映射772, 检查1390 = 缓存203(路径766.tool, 映射772, 路径766.work)
    if 检查1390 == 'python':
        键63.ok('aligned in python · arsc stored, 4 byte and page boundaries')
    elif 检查1390:
        键63.ok('zipalign applied')
    if args.unsigned:
        键63.info('unsigned build requested')
    else:
        源1500, 目标1501 = 路径206(路径766.tool, 映射772, 路径766.work, args.password)
        if 源1500:
            键63.ok('signed · ' + 目标1501)
        else:
            键63.bad('no signer available · install apksigner')
            return 7
    键63.head('verification', 文本28)
    步骤298(映射772, 路径766.tool)
    数据328(映射772)
    状态329(映射772)
    缓存283()
    键63.head('result', 文本28)
    报告1039 = 步骤218(映射772)
    节点1057 = 值102(映射772)
    索引284('artifact', [str(映射772), 'size      ' + 表104(报告1039['size']), 'sha256    ' + 节点1057[:40], 'strategy  ' + str(映射732)], 文本28)
    键63.kv('sha256', 节点1057)
    return 0

def 缓存283():
    计数5.close()
    if not 计数5.records:
        return
    total = sum((行785 for 读取1112, 行785 in 计数5.records)) or 1e-09
    计数1085 = max((行785 for 读取1112, 行785 in 计数5.records)) or 1e-09
    print()
    print('  ' + 目标61(缓存3.clamp(20, 78), 行25, 索引44))
    print('  ' + 索引4(状态9, True)('STAGE TIMINGS') + 打开33('   total %.2fs' % total))
    print('  ' + 目标61(缓存3.clamp(20, 78), 行25, 索引44))
    for name, 步骤1418 in 计数5.records:
        栈1419 = 步骤1418 / 计数1085
        节点1337 = max(1, int(栈1419 * 18))
        bar = 栈59('█' * 节点1337, 列26)
        扫描1077 = 100.0 * 步骤1418 / total
        print('  ' + 打开33(节点57(name.upper(), 22).ljust(23)) + bar + 打开33('  %6.2fs  %4.1f%%' % (步骤1418, 扫描1077)))
    spark = 键63.spark([行785 for 读取1112, 行785 in 计数5.records], 行25)
    if spark:
        print('  ' + 打开33('profile'.ljust(23)) + spark)
    print('  ' + 目标61(缓存3.clamp(20, 78), 行25, 索引44))

def 索引284(键703, 打开793, 句柄696=None):
    句柄696 = 句柄696 or 文本28
    列表847 = [''] + ['  ' + 名字909 for 名字909 in 打开793] + ['']
    值702 = 值62(列表847, 句柄696)
    if not 缓存3.enabled:
        for 目标1421 in 值702:
            print(目标1421)
        return
    列表1087 = lambda 条目693: re.sub('\\033\\[[0-9;?]*[A-Za-z]', '', 条目693)
    写入711 = [列表1087(目标1421) for 目标1421 in 值702]
    列946 = max((len(值1062) for 值1062 in 写入711))
    total = len(写入711)
    sys.stdout.write(索引4.HIDE)
    try:
        for 读取912 in range(total + 1):
            步骤58.paint([栈59(值1062, 句柄696) if 标记1490 < 读取912 else '' for 标记1490, 值1062 in enumerate(写入711)])
            time.sleep(0.03)
        for 读取952 in range(8):
            变量1280 = 读取952 / 7.0 * (列946 + 20) - 10
            文本708 = []
            for 值1062 in 写入711:
                计数805 = []
                for 参数1561, 目标701 in enumerate(值1062):
                    if 目标701 == ' ':
                        计数805.append(' ')
                        continue
                    行785 = abs(参数1561 - 变量1280)
                    构建1675 = max(0.0, 1.0 - 行785 / 9.0)
                    计数805.append(索引4(列表7(数据8(句柄696, 参数1561 / max(1, 列946 - 1)), 值22, 构建1675), True)(目标701))
                文本708.append(''.join(计数805))
            步骤58.paint(文本708)
            time.sleep(0.028)
    finally:
        sys.stdout.write(索引4.SHOW)
    步骤58.paint([栈59(值1062, 句柄696) for 值1062 in 写入711])
    步骤58.close()

def 计数285(args):
    计数5.reset()
    缓存3.probe()
    关闭714 = args.no_anim or not 缓存3.enabled
    if not args.quiet:
        节点97(关闭714)
        print()
    状态729, 键1383 = 条目573(args.input)
    if not 状态729.exists():
        键63.bad('input not found: ' + str(状态729))
        return 2
    键63.head('detection only', 行25)
    键63.info('no java · no apktool · reads the archive directly')
    区块815 = 列266(状态729)
    报告1039 = 步骤218(状态729)
    键63.kv('entries', 报告1039['files'])
    键63.kv('payload', 'dex %d · res %d · assets %d · libs %d' % (报告1039['dex'], 报告1039['res'], 报告1039['assets'], 报告1039['libs']))
    索引884 = None
    try:
        with zipfile.ZipFile(状态729) as 键1023:
            索引884 = 区块615(键1023)[1]
    except Exception:
        索引884 = None
    if 索引884:
        关闭234(索引884)
    else:
        键63.warn('manifest unreadable')
    节点377(句柄376(状态729))
    数据1088 = 字节267(区块815['names'])
    键63.head('runtime', 列26)
    if not 数据1088:
        键63.info('no managed runtime fingerprint')
    for 修补718, 索引1404, 偏移1374, evidence in 数据1088:
        键63.kv('%s · %s' % (修补718, 索引1404), ', '.join(evidence), width=30)
    栈779 = 读取232(None, [], 索引884) if 索引884 else []
    if 栈779:
        修补238(栈779)
    缓存283()
    print()
    print('  ' + 目标61(缓存3.clamp(20, 78), 文本28))
    键63.ok('detection complete · nothing was modified')
    return 0

def 路径286(args):
    计数5.reset()
    缓存3.probe()
    关闭714 = args.no_anim or not 缓存3.enabled
    if not args.quiet:
        节点97(关闭714)
        print()
    值1382, 键1383 = 条目573(args.input)
    if not 值1382.exists():
        键63.bad('input not found: ' + str(值1382))
        return 2
    区块1015 = 值1382.suffix.lower()
    if not 检查310(值1382):
        return 8
    写入751 = Path(tempfile.mkdtemp(扫描717='arp_re_'))
    构建795 = []
    解析796 = time.strftime('%Y-%m-%d %H:%M:%S')
    键63.head('target', 行25)
    键63.kv('input', 值1382.name)
    键63.kv('size', 表104(值1382.stat().st_size))
    键63.kv('format', (映射172(值1382) or 'unknown').upper())
    if 区块1015 == '.so':
        数据848 = 行265(值1382)
        参数281('native object', 字节27)
        if not 数据848.ok:
            键63.bad('not a readable ELF object')
            return 3
        节点697 = 数据848.summary()
        键63.kv('machine', '%s · %d-bit' % (节点697['machine'], 节点697['bits']))
        键63.kv('sections', 节点697['sections'])
        键63.kv('exports', 节点697['exports'])
        for 名字989, 步骤818 in 节点697['hardening'].items():
            键63.kv(名字989, 'enabled' if 步骤818 else 'absent', 写入791=关闭34 if 步骤818 else 构建35)
        构建795.append(('Native object', [('kv', [('machine', 节点697['machine']), ('bits', 节点697['bits']), ('sections', 节点697['sections']), ('exports', 节点697['exports'])]), ('chips', ['%s=%s' % (名字989, 步骤818) for 名字989, 步骤818 in 节点697['hardening'].items()])]))
        列表287(args, 值1382, 构建795, 解析796, {'elf': 节点697})
        return 0
    if 区块1015 == '.dex':
        值1422 = 源260(值1382.read_bytes(), 值1382.name)
        参数281('dex payload', 字节27)
        if not 值1422.valid:
            键63.bad('not a valid dex container')
            return 3
        节点697 = 值1422.summary()
        键63.kv('version', 节点697['version'])
        键63.kv('classes', 节点697['classes'])
        键63.kv('methods', 节点697['methods'])
        键63.kv('strings', 节点697['strings'])
        构建795.append(('DEX', [('kv', [('version', 节点697['version']), ('classes', 节点697['classes']), ('methods', 节点697['methods']), ('fields', 节点697['fields']), ('strings', 节点697['strings'])])]))
        列表287(args, 值1382, 构建795, 解析796, {'dex': 节点697})
        return 0
    if 区块1015 == '.ipa':
        info = 关闭274(值1382)
        参数281('ios package', 字节27)
        键63.kv('bundle', info['bundle'])
        键63.kv('display name', info['name'])
        键63.kv('version', info['version'])
        键63.kv('entries', info.get('entries', 0))
        键63.kv('frameworks', len(info['frameworks']))
        for 读取952 in info['frameworks'][:12]:
            键63.bullet(读取952)
        构建795.append(('iOS package', [('kv', [('bundle', info['bundle']), ('name', info['name']), ('version', info['version']), ('entries', info.get('entries', 0))]), ('chips', info['frameworks'][:40])]))
        列表287(args, 值1382, 构建795, 解析796, {'ipa': info})
        return 0
    扫描757 = 构建195(写入751, allow_net=not args.no_net, 缓存723=args.quiet)
    if 区块1015 == '.aab':
        参数281('bundle conversion', 文本28)
        键743, 目标1501 = 构建275(值1382, 写入751, 扫描757, args.password)
        if not 键743:
            键63.warn('bundle could not be built into a universal apk · ' + 目标1501)
            键63.info('falling back to direct bundle inspection')
        else:
            键63.ok('universal apk produced · ' + 目标1501)
            值1382 = 键743
    if 区块1015 == '.aab' and (not 值1382.suffix.lower() == '.apk'):
        区块815 = 列266(值1382)
        参数281('bundle inventory', 列26)
        键63.kv('entries', 区块815['total'])
        键63.kv('modules', sum((1 for 步骤698 in 区块815['names'] if 步骤698.startswith('base/') or 步骤698.endswith('/manifest/AndroidManifest.xml'))))
        构建795.append(('Bundle', [('kv', [('entries', 区块815['total'])]), ('chips', [步骤698 for 步骤698 in 区块815['names'] if 步骤698.endswith('AndroidManifest.xml')][:20])]))
        列表287(args, 值1382, 构建795, 解析796, {'bundle_index': {'total': 区块815['total']}})
        return 0
    列表767, 行705, 关闭754 = 句柄176(值1382, 写入751, 扫描757)
    if not 列表767:
        键63.bad('cannot read this archive · ' + 队列171(值1382))
        return 4
    键63.kv('resolved', 列表767.name)
    if 关闭754:
        键63.ok('%d splits · base %s' % (len(关闭754), 列表767.name))
    区块815 = 列266(列表767)
    报告1039 = 步骤218(列表767)
    参数281('container', 列26)
    键63.kv('entries', 报告1039['files'])
    键63.kv('payload', 'dex %d · res %d · assets %d · libs %d' % (报告1039['dex'], 报告1039['res'], 报告1039['assets'], 报告1039['libs']))
    if 报告1039['abi']:
        键63.kv('abis', ' · '.join(报告1039['abi']))
    构建795.append(('Container', [('kv', [('size', 表104(报告1039['size'])), ('entries', 报告1039['files']), ('dex', 报告1039['dex']), ('resources', 报告1039['res']), ('assets', 报告1039['assets']), ('native', 报告1039['libs'])]), ('chips', 报告1039['abi'])]))
    参数281('runtimes', 字节27)
    数据1088 = 字节267(区块815['names'])
    if not 数据1088:
        键63.info('no managed runtime fingerprint')
    for 修补718, 索引1404, 偏移1374, evidence in 数据1088:
        键63.kv('%s · %s' % (修补718, 索引1404), ', '.join(evidence), width=30, 写入791=修补38)
    构建795.append(('Runtimes', [('table', (['Framework', 'Language', 'Evidence'], [[名字909[0], 名字909[1], ', '.join(名字909[3])] for 名字909 in 数据1088]))] if 数据1088 else [('kv', [('result', 'none detected')])]))
    构建1075 = 文本268(区块815['names'])
    if 构建1075:
        参数281('language mix', 列26)
        检查1230 = max(构建1075.values())
        for 索引1404, 步骤698 in 构建1075.items():
            键63.bar(索引1404, 步骤698, 检查1230, width=24)
        构建795.append(('Language mix', [('bars', [(名字989, 步骤818, 检查1230, '#22d3ee') for 名字989, 步骤818 in 构建1075.items()])]))
    偏移774 = None
    try:
        with zipfile.ZipFile(列表767) as 键1023:
            if 'AndroidManifest.xml' in 键1023.namelist():
                偏移774 = 区块615(键1023)[1]
    except Exception:
        偏移774 = None
    if 偏移774:
        关闭234(偏移774)
        构建795.append(('Manifest', [('kv', [('package', 偏移774['package']), ('version', 偏移774['version']), ('min sdk', 偏移774['min_sdk']), ('target sdk', 偏移774['target_sdk']), ('launcher', 偏移774['launcher']), ('exported', 偏移774['exported']), ('debuggable', 偏移774['debuggable']), ('cleartext', 偏移774['cleartext'])]), ('chips', 偏移774['permissions'][:60])]))
    结果1042 = 名字269(列表767, None)
    if 结果1042:
        参数281('bytecode', 字节27)
        键1423 = sum((len(行785.classes) for 行785 in 结果1042))
        表1424 = sum((行785.methods for 行785 in 结果1042))
        键63.kv('dex files', len(结果1042))
        键63.kv('classes', 键1423)
        键63.kv('methods', 表1424)
        行1425 = {}
        for 行785 in 结果1042:
            for 名字989, 步骤818 in 行785.api_hits.items():
                行1425[名字989] = 行1425.get(名字989, 0) + 步骤818
        if 行1425:
            检查1230 = max(行1425.values())
            for 名字989, 步骤818 in sorted(行1425.items(), key=lambda kv: -kv[1])[:10]:
                键63.bar(名字989, 步骤818, 检查1230, width=22)
        列1426 = {}
        for 行785 in 结果1042:
            for 映射1132 in 行785.classes:
                值1062 = 映射1132['name'].rsplit('/', 1)[0] if '/' in 映射1132['name'] else '(default)'
                列1426[值1062] = 列1426.get(值1062, 0) + 1
        for 值1062, 步骤698 in sorted(列1426.items(), key=lambda kv: -kv[1])[:10]:
            键63.bullet('%s · %d classes' % (值1062, 步骤698))
        构建795.append(('Bytecode', [('kv', [('dex files', len(结果1042)), ('classes', 键1423), ('methods', 表1424)]), ('bars', [(名字989, 步骤818, max(行1425.values()), '#8b5cf6') for 名字989, 步骤818 in sorted(行1425.items(), key=lambda kv: -kv[1])[:12]]) if 行1425 else ('kv', [('api', 'none')])]))
        if args.dump:
            列表1607 = Path(args.dump).expanduser()
            列表1607.mkdir(parents=True, exist_ok=True)
            for 行785 in 结果1042:
                值702 = sorted({映射1132['name'] for 映射1132 in 行785.classes})
                行105(列表1607 / ('%s.classes.txt' % 行785.name), '\n'.join(值702), 'w')
                行105(列表1607 / ('%s.strings.txt' % 行785.name), '\n'.join(行785.strings[:200000]), 'w')
            键63.ok('class and string dumps written to ' + str(列表1607))
    状态1089 = 检查270(列表767, None)
    if 状态1089:
        参数281('resources', 列26)
        字节1427 = 状态1089.summary()
        键63.kv('packages', ', '.join(字节1427['packages']) or '?')
        键63.kv('types', 字节1427['type_count'])
        键63.kv('entries', 字节1427['entries'])
        检查1230 = max(字节1427['by_type'].values()) if 字节1427['by_type'] else 1
        for 名字989, 步骤818 in list(字节1427['by_type'].items())[:10]:
            键63.bar(名字989, 步骤818, 检查1230, width=22)
        构建795.append(('Resources', [('kv', [('packages', ', '.join(字节1427['packages'])), ('types', 字节1427['type_count']), ('entries', 字节1427['entries'])]), ('bars', [(名字989, 步骤818, 检查1230, '#34d399') for 名字989, 步骤818 in list(字节1427['by_type'].items())[:14]])]))
    报告839 = 打开273(列表767, None)
    if 报告839:
        参数281('native objects', 字节27)
        打开793 = []
        for 修补958 in 报告839[:24]:
            节点697 = 修补958.summary()
            解析956 = 节点697['hardening']
            表1024 = ''.join(['P' if 解析956.get('pie') else '-', 'N' if 解析956.get('nx') else '-', 'R' if 解析956.get('relro') else '-', 'C' if 解析956.get('canary') else '-'])
            键63.kv(修补958.name, '%s · %d-bit · %s · %s' % (节点697['machine'], 节点697['bits'], 表104(节点697['size']), 表1024), width=34)
            打开793.append([修补958.name, 节点697['machine'], 节点697['bits'], 节点697['sections'], 节点697['exports'], 表1024])
        键63.info('hardening key: P=pie N=nx R=relro C=canary')
        构建795.append(('Native objects', [('table', (['Object', 'ISA', 'Bits', 'Sections', 'Exports', 'Hardening'], 打开793))]))
    扫描837 = 句柄376(列表767)
    节点377(扫描837)
    if args.disasm and 报告839:
        参数281('disassembly', 字节27)
        for 修补958 in 报告839[:4]:
            值702, 名字709 = 步骤378(修补958.path, limit=args.disasm)
            if 名字709:
                键63.warn('%s · %s' % (修补958.name, 名字709))
                break
            键63.kv(修补958.name, '%d instructions' % len(值702), width=30)
            for 计数885 in 值702[:12]:
                print('    ' + 索引4(栈19)(计数885))
    if args.java:
        参数281('java sources', 文本28)
        关闭1034, 结果922 = 目标381(写入751, 列表767, args.java)
        if 关闭1034:
            键63.ok('java tree · ' + 结果922)
        else:
            键63.warn(结果922)
    状态809, 状态1129 = 检查350(列表767)
    if 状态809 or 状态1129:
        参数281('pinning & endpoints', 字节27)
        for 修补718, 数据1608 in sorted(状态809.items()):
            键63.kv(修补718, '%d class(es)' % len(数据1608), width=28)
            for 行785 in list(数据1608)[:3]:
                键63.bullet(节点57(行785, 70))
        if 状态1129:
            键63.kv('endpoints', len(状态1129), width=28)
            for 修补1318 in 状态1129[:18]:
                print('    ' + 打开33(路径46 + ' ' + 修补1318))
        构建795.append(('Pinning', [('kv', [(名字989, '%d class(es)' % len(步骤818)) for 名字989, 步骤818 in sorted(状态809.items())]), ('chips', 状态1129[:60])]))
    if args.frida:
        dest = Path(args.frida).expanduser()
        行105(dest, 参数361(状态809, 列表767.name), 'w')
        键63.ok('frida hook script · ' + str(dest))
    if args.mapping:
        映射812 = 结果362(args.mapping)
        文本1428 = sum((1 for 行785 in 结果1042 for 映射1132 in 行785.classes if 映射1132['name'] in 映射812))
        键63.kv('proguard names', '%d resolvable of %d entries' % (文本1428, len(映射812)))
    if args.unpack:
        dest = Path(args.unpack).expanduser()
        dest.mkdir(parents=True, exist_ok=True)
        参数281('extraction', 文本28)
        列866 = 0
        try:
            with zipfile.ZipFile(列表767) as 键1023:
                for info in 键1023.infolist():
                    关闭794 = dest / info.filename
                    if info.is_dir():
                        关闭794.mkdir(parents=True, exist_ok=True)
                        continue
                    关闭794.parent.mkdir(parents=True, exist_ok=True)
                    with 键1023.open(info) as 键1743, open(关闭794, 'wb') as 表1744:
                        shutil.copyfileobj(键1743, 表1744)
                    列866 += 1
        except Exception as 修补958:
            键63.warn('extraction incomplete · ' + 节点57(str(修补958), 60))
        键63.ok('%d entries written byte-for-byte to %s' % (列866, dest))
        if 扫描757.get('apktool') and args.decode:
            状态729 = dest / '_smali'
            字节707, 读取1112 = 关闭114(列186(扫描757['apktool']) + ['d', '-f', str(列表767), '-o', str(状态729)], 'apktool decode', timeout=3600)
            if 状态729.exists():
                键63.ok('smali tree · ' + str(状态729))
        构建795.append(('Extraction', [('kv', [('entries written', 列866), ('destination', str(dest))])]))
    列表287(args, 值1382, 构建795, 解析796, {'container': 报告1039, 'runtimes': [名字909[0] for 名字909 in 数据1088], 'languages': 构建1075, 'manifest': {名字989: 步骤818 for 名字989, 步骤818 in (偏移774 or {}).items() if 名字989 != 'raw'}, 'dex': [行785.summary() for 行785 in 结果1042], 'resources': 状态1089.summary() if 状态1089 else None, 'native': [修补958.summary() for 修补958 in 报告839]})
    shutil.rmtree(写入751, ignore_errors=True)
    return 0

def 列表287(args, 关闭794, 构建795, 解析796, 参数761):
    条目1053 = Path(args.output).expanduser() if args.output else HOME / ('%s_RE' % 关闭794.stem)
    if 条目1053.suffix:
        条目1053 = 条目1053.parent
    条目1053.mkdir(parents=True, exist_ok=True)
    if not args.no_report:
        读取792 = {'title': 'Reverse engineering report', 'target': 关闭794.name, 'stamp': 解析796, 'sections': 构建795}
        检查1150 = 修补278(读取792)
        dest = 条目1053 / 'report.html'
        行105(dest, 检查1150, 'w')
        print()
        print('  ' + 栈59(str(dest), 文本28, True))
    标记1090 = 条目1053 / 'report.json'
    参数721 = dict(参数761)
    参数721.update({'tool': 写入71, 'version': 读取72, 'target': str(关闭794), 'stamp': 解析796})
    行105(标记1090, json.dumps(参数721, indent=2, default=str), 'w')
    键63.kv('json', str(标记1090))
    键63.kv('directory', str(条目1053))
数据288 = 55605
状态289 = b'PK\x03\x04'
标记290 = b'PK\x07\x08'

def 队列291(变量720):
    文本708 = []
    try:
        with open(变量720, 'rb') as 读取952:
            读取952.seek(0, 2)
            关闭914 = 读取952.tell()
            读取952.seek(0)
            列986 = 0
            while 列986 < 300000:
                列986 += 1
                sig = 读取952.read(4)
                if len(sig) < 4 or sig != 状态289:
                    break
                映射1652 = 读取952.read(26)
                if len(映射1652) < 26:
                    break
                表1024, 条目1453 = (struct.unpack_from('<H', 映射1652, 2)[0], struct.unpack_from('<H', 映射1652, 4)[0])
                读取1352 = struct.unpack_from('<I', 映射1652, 14)[0]
                关闭1754, 构建1755 = (struct.unpack_from('<H', 映射1652, 22)[0], struct.unpack_from('<H', 映射1652, 24)[0])
                name = 读取952.read(关闭1754).decode('utf-8', 'replace')
                读取952.read(构建1755)
                偏移894 = 读取952.tell()
                文本708.append({'name': name, 'method': 条目1453, 'offset': 偏移894, 'size': 读取1352, 'flags': 表1024})
                读取952.seek(偏移894 + 读取1352)
                if 表1024 & 8:
                    if 读取952.read(4) == 标记290:
                        读取952.seek(12, 1)
                if 读取952.tell() >= 关闭914:
                    break
    except Exception:
        pass
    return 文本708

def 映射292(状态729, 扫描797, 修补798, 报告799, 变量800):
    with zipfile.ZipFile(状态729) as 名字1429, zipfile.ZipFile(扫描797, 'w') as 检查1430:
        for 区块1415 in 名字1429.infolist():
            参数721 = 名字1429.read(区块1415.filename)
            状态1609 = zipfile.ZipInfo(区块1415.filename, date_time=区块1415.date_time)
            状态1609.compress_type = 区块1415.compress_type
            状态1609.external_attr = 区块1415.external_attr
            状态1609.internal_attr = 区块1415.internal_attr
            状态1609.create_system = 区块1415.create_system
            if 区块1415.filename == 'resources.arsc':
                状态1609.compress_type = zipfile.ZIP_STORED
            if 状态1609.compress_type == zipfile.ZIP_STORED:
                键1703 = 变量800 if 区块1415.filename.endswith('.so') else 报告799
                want = 修补798.get(区块1415.filename)
                if want is None:
                    变量1280 = 检查1430.fp.tell()
                    键863 = 30 + len(区块1415.filename.encode('utf-8'))
                    want = -(变量1280 + 键863) % 键1703
                if want < 4:
                    want += 键1703
                状态1609.extra = struct.pack('<HH', 数据288, want - 4) + b'\x00' * (want - 4)
            else:
                状态1609.extra = b''
            检查1430.writestr(状态1609, 参数721)

def 条目293(键743, 报告799=4, 变量800=4096):
    结果82('align %s' % Path(键743).name)
    状态729 = Path(键743)
    扫描797 = 状态729.with_name(状态729.name + '.aligned')
    修补798 = {}
    try:
        for 句柄1376 in range(3):
            映射292(状态729, 扫描797, 修补798, 报告799, 变量800)
            区块855 = 队列291(扫描797)
            bad = []
            for 修补958 in 区块855:
                if 修补958['method'] != 0:
                    continue
                键1703 = 变量800 if 修补958['name'].endswith('.so') else 报告799
                if 修补958['offset'] % 键1703:
                    bad.append((修补958['name'], 修补958['offset'] % 键1703))
            if not bad:
                os.replace(扫描797, 状态729)
                return True
            for name, 表1704 in bad:
                current = 修补798.get(name)
                if current is None:
                    with zipfile.ZipFile(扫描797) as 键1023:
                        info = 键1023.getinfo(name)
                    current = len(info.extra) or 键1703
                修补798[name] = max(4, current + (键1703 - 表1704) % 键1703)
        os.replace(扫描797, 状态729)
        return False
    except Exception:
        if 扫描797.exists():
            扫描797.unlink(missing_ok=True)
        return False
偏移294 = {'UPDATE_INCOMPATIBLE': 'INSTALL_FAILED_UPDATE_INCOMPATIBLE', 'PARSE_NO_CERT': 'INSTALL_PARSE_FAILED_NO_CERTIFICATES', 'INCONSISTENT_CERT': 'INSTALL_PARSE_FAILED_INCONSISTENT_CERTIFICATES', 'INVALID_APK': 'INSTALL_FAILED_INVALID_APK', 'NO_V2': 'INSTALL_PARSE_FAILED_NO_CERTIFICATES (v2 missing on android 11+)'}

def 区块295(扫描757, 键743):
    if not 扫描757 or not 扫描757.get('apksigner'):
        return []
    字节707, 文本708, 名字709 = 检查110(列186(扫描757['apksigner']) + ['verify', '--verbose', str(键743)], timeout=600)
    text = (文本708 or '') + '\n' + (名字709 or '')
    句柄816 = []
    for 计数885 in text.splitlines():
        关闭1074 = 计数885.lower()
        if 'scheme' not in 关闭1074:
            continue
        if 'true' not in 关闭1074 and ': true' not in 关闭1074:
            continue
        句柄776 = re.search('\\bv(\\d+(?:\\.\\d+)?)\\s+scheme', 关闭1074)
        if 句柄776:
            映射732 = 'v' + 句柄776.group(1)
            if 映射732 not in 句柄816:
                句柄816.append(映射732)
    return 句柄816

def 句柄296(键743):
    结果82('strip META-INF in %s' % Path(键743).name)
    状态729 = Path(键743)
    扫描797 = 状态729.with_name(状态729.name + '.nosig')
    句柄1056 = []
    try:
        with zipfile.ZipFile(状态729) as 名字1429, zipfile.ZipFile(扫描797, 'w') as 检查1430:
            for 区块1415 in 名字1429.infolist():
                行1705 = 区块1415.filename.upper()
                if 行1705.startswith('META-INF/') and 行1705.endswith(('.SF', '.RSA', '.DSA', '.EC', '.MF')):
                    句柄1056.append(区块1415.filename)
                    continue
                状态1609 = zipfile.ZipInfo(区块1415.filename, date_time=区块1415.date_time)
                状态1609.compress_type = 区块1415.compress_type
                状态1609.external_attr = 区块1415.external_attr
                状态1609.internal_attr = 区块1415.internal_attr
                状态1609.create_system = 区块1415.create_system
                检查1430.writestr(状态1609, 名字1429.read(区块1415.filename))
        os.replace(扫描797, 状态729)
        return 句柄1056
    except Exception:
        if 扫描797.exists():
            扫描797.unlink(missing_ok=True)
        return []

def 节点297(键743, 扫描757=None):
    索引924 = []
    区块855 = 队列291(键743)
    数据728 = {修补958['name'] for 修补958 in 区块855}
    关闭834 = None
    文本1028 = []
    队列1091 = False
    if 扫描757 and 扫描757.get('apksigner'):
        关闭834 = 表304(扫描757, 键743)
        队列1091 = bool(关闭834 and 关闭834.get('ok'))
        if 队列1091:
            文本1028 = 区块295(扫描757, 键743)
    for 目标821, 写入1431, 关闭1114 in 列表327(键743):
        读取1432 = [句柄776 for 节点697, 句柄776 in 关闭1114 if 节点697 == 'bad']
        if 读取1432:
            索引924.append(('bad', 偏移294['INVALID_APK'], '%s fails dex verification · %s' % (目标821, 读取1432[0]), "patch that dex with baksmali/smali or keep every item's length"))
        else:
            标记1450 = [句柄776 for 节点697, 句柄776 in 关闭1114 if 节点697 == 'warn']
            if 标记1450:
                索引924.append(('warn', 'INSTALL_OK', '%s · %s' % (目标821, 标记1450[0]), 're-check with dexdump if the app misbehaves'))
    状态1089 = next((修补958 for 修补958 in 区块855 if 修补958['name'] == 'resources.arsc'), None)
    if 状态1089 is None:
        索引924.append(('bad', 偏移294['INVALID_APK'], 'resources.arsc is missing', 'rebuild the resources'))
    else:
        if 状态1089['method'] != 0:
            索引924.append(('bad', 偏移294['INVALID_APK'], 'resources.arsc is compressed', 'rebuild with a tool that stores it uncompressed'))
        if 状态1089['offset'] % 4:
            索引924.append(('bad', 偏移294['INVALID_APK'], 'resources.arsc is not 4 byte aligned', 'run with alignment enabled'))
    try:
        打开1433 = 文本548(Path(键743).read_bytes())
    except Exception:
        打开1433 = {'status': 'unknown', 'schemes': [], 'detail': 'could not read'}
    if 打开1433['status'] == 'stale':
        索引924.append(('bad', 偏移294['INCONSISTENT_CERT'], 'stale %s signature block · %s' % ('/'.join(打开1433['schemes']) or 'apk', 打开1433['detail']), 'run: arpxtool repair'))
    elif 打开1433['status'] == 'valid' and (not 队列1091):
        队列1091 = True
        文本1028 = 打开1433['schemes']
    映射1092 = [步骤698 for 步骤698 in 数据728 if 步骤698.upper().startswith('META-INF/') and 步骤698.upper().endswith(('.SF', '.RSA', '.DSA', '.EC'))]
    if 映射1092:
        源1260 = {Path(步骤698).stem for 步骤698 in 映射1092}
        if 队列1091 and len(源1260) <= 1:
            pass
        elif 队列1091 and len(源1260) > 1:
            索引924.append(('bad', 偏移294['INCONSISTENT_CERT'], '%d different signature blocks inside META-INF' % len(源1260), 'strip META-INF and sign once'))
        elif 关闭834 is not None and (not 关闭834.get('ok')):
            索引924.append(('bad', 偏移294['INCONSISTENT_CERT'], '%d signature file(s) present but verification failed' % len(映射1092), 'strip META-INF before signing'))
        else:
            索引924.append(('info', '-', '%d signature file(s) in META-INF, signer not available to verify' % len(映射1092), 'install apksigner for a definitive check'))
    条目1093 = [修补958 for 修补958 in 区块855 if 修补958['name'].endswith('.so')]
    索引884 = None
    try:
        with zipfile.ZipFile(键743) as 键1023:
            索引884 = 区块615(键1023)[1]
    except Exception:
        索引884 = None
    偏移1094 = bool(索引884 and 索引884.get('extract_native_libs') == 'false')
    if 条目1093 and 偏移1094:
        关闭1434 = [修补958 for 修补958 in 条目1093 if 修补958['method'] != 0]
        步骤1098 = [修补958 for 修补958 in 条目1093 if 修补958['method'] == 0 and 修补958['offset'] % 4096]
        if 关闭1434:
            索引924.append(('bad', 偏移294['INVALID_APK'], '%d native object(s) compressed while extractNativeLibs=false' % len(关闭1434), 'store the .so entries uncompressed'))
        if 步骤1098:
            索引924.append(('bad', 偏移294['INVALID_APK'], '%d native object(s) not page aligned' % len(步骤1098), 'align .so entries to 4096'))
    elif 条目1093:
        步骤1098 = [修补958 for 修补958 in 条目1093 if 修补958['method'] == 0 and 修补958['offset'] % 4096]
        if 步骤1098:
            索引924.append(('info', '-', '%d native object(s) not page aligned (only matters when extractNativeLibs=false)' % len(步骤1098), 'harmless with the default extractNativeLibs=true'))
    if 'AndroidManifest.xml' not in 数据728:
        索引924.append(('bad', 偏移294['INVALID_APK'], 'AndroidManifest.xml missing', 'rebuild the archive'))
    if not any((re.match('classes\\d*\\.dex$', 步骤698) for 步骤698 in 数据728)):
        索引924.append(('bad', 偏移294['INVALID_APK'], 'no dex payload', 'rebuild the archive'))
    if 队列1091:
        if not any((节点697 in ('v2', 'v3', 'v3.1') for 节点697 in 文本1028)):
            索引924.append(('bad', 偏移294['NO_V2'], 'no v2/v3 signature found (schemes: %s)' % (', '.join(文本1028) or 'none'), 're-sign with --v2-signing-enabled true'))
    elif 关闭834 is not None and (not 关闭834.get('ok')):
        索引924.append(('bad', 偏移294['PARSE_NO_CERT'], 'apksigner verify failed', 'sign the archive with apksigner'))
    return (索引924, 关闭834, 索引884)

def 步骤298(键743, 扫描757=None):
    索引924, 关闭834, 索引884 = 节点297(键743, 扫描757)
    键63.head('install diagnosis', 字节27)
    if 索引884:

        def _val(步骤818):
            return 'unavailable' if 步骤818 in (None, '', '?') else str(步骤818)
        键63.kv('package', _val(索引884.get('package')), width=18)
        键63.kv('version', '%s (%s)' % (_val(索引884.get('version')), _val(索引884.get('version_code'))), width=18)
        键63.kv('sdk', '%s -> %s' % (_val(索引884.get('min_sdk')), _val(索引884.get('target_sdk'))), width=18)
        键63.kv('extractNativeLibs', _val(索引884.get('extract_native_libs')), width=18)
        if 索引884.get('package_recovered'):
            键63.info('package name was recovered from the string pool · the binary manifest is only partly decodable')
    if 关闭834 and 关闭834.get('ok'):
        键63.kv('certificate', 节点57(关闭834.get('subject', '?'), 52), width=18)
        if 关闭834.get('sha256'):
            键63.kv('sha-256', 节点57(关闭834['sha256'], 52), width=18)
    if not 索引924:
        键63.ok('no install blocker found in the archive')
        return True
    写入791 = {'bad': 解析36, 'warn': 构建35, 'info': 扫描37}
    区块1095 = {'bad': 状态49, 'warn': 队列51, 'info': 列表47}
    for 区块775, code, 表704, 数据928 in 索引924:
        print('  ' + 写入791[区块775](区块1095[区块775]) + ' ' + 修补38(表704))
        if code and code != '-':
            print('    ' + 打开33('code  ' + code))
        print('    ' + 打开33('fix   ' + 数据928))
    return not any((节点697 == 'bad' for 节点697, 读取1112, 读取1112, 读取1112 in 索引924))

def 栈299(args):
    缓存3.probe()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    键743, 键1383 = 条目573(args.input)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    扫描757 = 构建195(Path(tempfile.mkdtemp()), allow_net=False, 缓存723=True)
    ok = 步骤298(键743, 扫描757)
    print()
    键63.info('if the original build is still installed, android refuses the update:')
    键63.info('  adb uninstall <package>   or   uninstall from settings, then install')
    return 0 if ok else 6

def 源300(键743):
    索引924 = []
    区块855 = 队列291(键743)
    数据728 = [修补958['name'] for 修补958 in 区块855]
    if not 区块855:
        return ([('bad', 'zip central directory unreadable')], False)
    句柄1096 = set()
    节点1097 = 0
    for 步骤698 in 数据728:
        if 步骤698 in 句柄1096:
            节点1097 += 1
        句柄1096.add(步骤698)
    if 节点1097:
        索引924.append(('bad', '%d duplicate archive entries' % 节点1097))
    状态1089 = next((修补958 for 修补958 in 区块855 if 修补958['name'] == 'resources.arsc'), None)
    if 状态1089 is None:
        索引924.append(('warn', 'resources.arsc missing'))
    else:
        if 状态1089['method'] != 0:
            索引924.append(('bad', 'resources.arsc is compressed · android 11+ rejects this'))
        if 状态1089['offset'] % 4:
            索引924.append(('bad', 'resources.arsc not 4 byte aligned (offset %d)' % 状态1089['offset']))
    步骤1098 = [修补958 for 修补958 in 区块855 if 修补958['method'] == 0 and 修补958['offset'] % 4]
    if 步骤1098:
        索引924.append(('warn', '%d stored entries not 4 byte aligned' % len(步骤1098)))
    栈1099 = [修补958 for 修补958 in 区块855 if 修补958['method'] == 0 and 修补958['name'].endswith('.so') and 修补958['offset'] % 4096]
    if 栈1099:
        索引924.append(('info', '%d native objects not page aligned' % len(栈1099)))
    源1100 = [步骤698 for 步骤698 in 数据728 if os.path.basename(步骤698).startswith('$')]
    if 源1100:
        索引924.append(('bad', '%d resource entries still start with $' % len(源1100)))
    目标1101 = [步骤698 for 步骤698 in 数据728 if 步骤698.startswith('/') or '\\' in 步骤698 or '..' in 步骤698.split('/')]
    if 目标1101:
        索引924.append(('bad', '%d unsafe archive paths' % len(目标1101)))
    if 'AndroidManifest.xml' not in 句柄1096:
        索引924.append(('bad', 'AndroidManifest.xml missing'))
    if not any((re.match('classes\\d*\\.dex$', 步骤698) for 步骤698 in 数据728)):
        索引924.append(('bad', 'no dex payload'))
    for 目标821, 写入1431, 关闭1114 in 列表327(键743):
        读取1432 = [句柄776 for 节点697, 句柄776 in 关闭1114 if 节点697 == 'bad']
        if 读取1432:
            索引924.append(('bad', '%s fails dex verification · %s' % (目标821, 读取1432[0])))
        else:
            标记1450 = [句柄776 for 节点697, 句柄776 in 关闭1114 if 节点697 == 'warn']
            if 标记1450:
                索引924.append(('warn', '%s · %s' % (目标821, 标记1450[0])))
    值1102 = 状态1089 and 状态1089['method'] == 0 and (状态1089['offset'] % 4 == 0)
    return (索引924, 值1102)

def 目标301(键743):
    节点857 = 源300(键743)
    索引924 = 节点857[0] if isinstance(节点857, tuple) else 节点857
    写入791 = {'bad': 解析36, 'warn': 构建35, 'info': 扫描37}
    区块1095 = {'bad': 状态49, 'warn': 队列51, 'info': 列表47}
    if not 索引924:
        键63.ok('installability audit clean · alignment, arsc, paths all valid')
        return True
    for 区块775, 表704 in 索引924:
        print('  ' + 写入791[区块775](区块1095[区块775]) + ' ' + 修补38(表704))
    return not any((节点697 == 'bad' for 节点697, 读取1112 in 索引924))

def 值302(队列691, 映射692):
    解析1436, 扫描1437 = ({}, {})
    for 变量720, 修补1438 in ((队列691, 解析1436), (映射692, 扫描1437)):
        try:
            with zipfile.ZipFile(变量720) as 键1023:
                for info in 键1023.infolist():
                    修补1438[info.filename] = (info.CRC, info.file_size, info.compress_size)
        except Exception:
            return None
    字节987 = sorted(set(扫描1437) - set(解析1436))
    句柄1056 = sorted(set(解析1436) - set(扫描1437))
    键1103 = sorted((名字989 for 名字989 in set(解析1436) & set(扫描1437) if 解析1436[名字989][0] != 扫描1437[名字989][0]))
    return {'added': 字节987, 'removed': 句柄1056, 'changed': 键1103, 'before': 解析1436, 'after': 扫描1437}

def 键303(键743, 参数801, limit=60):
    条目893 = 参数801.lower()
    步骤978 = []
    try:
        with zipfile.ZipFile(键743) as 键1023:
            for name in 键1023.namelist():
                if not re.search('\\.(dex|so|json|js|xml|txt|bundle|dat|properties|smali)$', name, re.I):
                    continue
                try:
                    参数721 = 键1023.read(name)
                except Exception:
                    continue
                if len(参数721) > 80 * 1024 * 1024:
                    continue
                for 句柄776 in re.finditer(re.escape(条目893.encode('utf-8', 'ignore')), 参数721.lower()):
                    start = max(0, 句柄776.start() - 60)
                    行1345 = 参数721[start:句柄776.start() + 120]
                    text = re.sub(b'[^\\x20-\\x7e]', b'.', 行1345).decode('ascii', 'ignore')
                    步骤978.append((name, 句柄776.start(), text))
                    if len(步骤978) >= limit:
                        return 步骤978
    except Exception:
        pass
    return 步骤978

def 表304(扫描757, 键743):
    if not 扫描757.get('apksigner'):
        return None
    字节707, 文本708, 名字709 = 检查110(列186(扫描757['apksigner']) + ['verify', '--print-certs', str(键743)], timeout=600)
    text = (文本708 or '') + (名字709 or '')
    关闭834 = {'ok': 字节707 == 0, 'raw': text}
    for 计数885 in text.splitlines():
        关闭1074 = 计数885.lower()
        for key, 修补718 in (('signer #1 certificate dn:', 'subject'), ('subject:', 'subject'), ('issuer:', 'issuer'), ('sha-256 digest:', 'sha256'), ('sha-1 digest:', 'sha1'), ('valid from:', 'valid')):
            if 关闭1074.startswith(key):
                关闭834[修补718] = 计数885.split(':', 1)[1].strip()
    return 关闭834

def 行305(结果802=6, 缓存803=False):
    表1104 = 0
    列866 = 0
    字节787 = Path(tempfile.gettempdir())
    行1105 = time.time()
    for 值1062 in 字节787.glob('arp_*'):
        try:
            if not 值1062.is_dir():
                continue
            if not 缓存803 and 行1105 - 值1062.stat().st_mtime < 结果802 * 3600:
                continue
            关闭914 = sum((读取952.stat().st_size for 读取952 in 值1062.rglob('*') if 读取952.is_file()))
            shutil.rmtree(值1062, ignore_errors=True)
            表1104 += 关闭914
            列866 += 1
        except Exception:
            pass
    return (列866, 表1104)

def 列306():
    缓存3.probe()
    节点97(not 缓存3.enabled)
    键63.head('workspace cleanup', 字节27)
    列866, 表1104 = 行305(0, 缓存803=True)
    键63.kv('trees removed', 列866)
    键63.kv('space reclaimed', 表104(表1104))
    键63.kv('free now', 表104(名字109(HOME)))
    for 偏移1014 in HOME.glob('*.arpbak'):
        try:
            偏移1014.unlink()
        except Exception:
            pass
    键63.ok('workspace clean')
    return 0

def 字节307(args):
    缓存3.probe()
    节点97(not 缓存3.enabled)
    列1106 = Path(tempfile.mkdtemp())
    队列691, 报告1439, 变量1440 = 句柄616(args.input, 列1106)
    映射692, 参数1441, 结果1442 = 句柄616(args.compare, 列1106)
    if 队列691 is None:
        键63.bad('input not found · ' + str(args.input))
        return 2
    if 映射692 is None:
        键63.bad('second input not found · ' + str(args.compare))
        return 2
    for 字节1107 in (报告1439, 参数1441):
        if 字节1107:
            键63.info(字节1107)
    for 值1062 in (队列691, 映射692):
        if not 值1062.exists():
            键63.bad('missing ' + str(值1062))
            return 2
    键63.head('archive diff', 列26)
    键63.kv('before', '%s · %s' % (队列691.name, 表104(队列691.stat().st_size)))
    键63.kv('after', '%s · %s' % (映射692.name, 表104(映射692.stat().st_size)))
    文本1108 = 值302(队列691, 映射692)
    if not 文本1108:
        键63.bad('one of the archives is unreadable')
        return 3
    键63.kv('added', len(文本1108['added']))
    键63.kv('removed', len(文本1108['removed']))
    键63.kv('changed', len(文本1108['changed']))
    for 修补718, key, 写入791 in (('added', 'added', 节点17), ('removed', 'removed', 键23), ('changed', 'changed', 区块15)):
        区块895 = 文本1108[key]
        if not 区块895:
            continue
        print()
        print('  ' + 索引4(写入791, True)(修补718.upper()) + 打开33(' · %d' % len(区块895)))
        for name in 区块895[:25]:
            print('    ' + 索引4(写入791)(路径46) + ' ' + 打开33(节点57(name, 90)))
        if len(区块895) > 25:
            print('    ' + 打开33('… %d more' % (len(区块895) - 25)))
    return 0

def 文本308(args):
    缓存3.probe()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    变量720, 键1383 = 条目573(args.input)
    if not 变量720.exists():
        键63.bad('missing ' + str(变量720))
        return 2
    键63.head('string search', 字节27)
    键63.kv('term', args.search)
    步骤978 = 键303(变量720, args.search)
    if not 步骤978:
        键63.info('no match')
        return 0
    键63.ok('%d match(es)' % len(步骤978))
    for name, 行745, text in 步骤978:
        print('  ' + 报告39(映射52) + ' ' + 修补38(节点57(name, 46)) + 打开33(' @ 0x%x' % 行745))
        print('    ' + 索引4(栈19)(节点57(text, 110)))
    return 0

def 名字309(args):
    缓存3.probe()
    节点97(not 缓存3.enabled)
    变量720, 键1383 = 条目573(args.input)
    if not 变量720.exists():
        键63.bad('missing ' + str(变量720))
        return 2
    扫描757 = 构建195(Path(tempfile.mkdtemp()), allow_net=False, 缓存723=True)
    键63.head('signature facts', 列26)
    关闭834 = 表304(扫描757, 变量720)
    if not 关闭834:
        键63.bad('apksigner unavailable')
        return 3
    if not 关闭834.get('ok'):
        键63.warn('signature does not verify')
    for key, 修补718 in (('subject', 'subject'), ('issuer', 'issuer'), ('sha256', 'sha-256'), ('sha1', 'sha-1'), ('valid', 'valid from')):
        if 关闭834.get(key):
            键63.kv(修补718, 关闭834[key])
    return 0

def 检查310(变量720, 索引804=True):
    关闭914 = 0
    try:
        关闭914 = Path(变量720).stat().st_size
    except Exception:
        pass
    名字1109 = max(2 * 1024 ** 3, 关闭914 * 14)
    状态1049 = 名字109(tempfile.gettempdir())
    if 状态1049 and 状态1049 < 名字1109:
        键63.warn('only %s free · this job wants about %s' % (表104(状态1049), 表104(名字1109)))
        列866, 表1104 = 行305(2) if 索引804 else (0, 0)
        if 列866:
            键63.ok('reclaimed %s from %d stale tree(s)' % (表104(表1104), 列866))
        if 名字109(tempfile.gettempdir()) < 名字1109 // 2:
            键63.bad('insufficient space · free up storage or point TMPDIR elsewhere')
            return False
    return True

class 写入311:

    def __init__(self, 参数721):
        self.d = 参数721
        self.ok = len(参数721) > 112 and 参数721[:4] == b'dex\n'
        self.s_n = self.s_off = self.t_n = self.t_off = 0
        self.m_n = self.m_off = self.c_n = self.c_off = 0
        self.p_n = self.p_off = 0
        self._scache = {}
        if not self.ok:
            return
        self.s_n, self.s_off = (句柄256(参数721, 56), 句柄256(参数721, 60))
        self.t_n, self.t_off = (句柄256(参数721, 64), 句柄256(参数721, 68))
        self.p_n, self.p_off = (句柄256(参数721, 72), 句柄256(参数721, 76))
        self.m_n, self.m_off = (句柄256(参数721, 88), 句柄256(参数721, 92))
        self.c_n, self.c_off = (句柄256(参数721, 96), 句柄256(参数721, 100))
        self._clamp(len(参数721))

    def _clamp(self, 关闭914):

        def fit(列866, 偏移894, 检查1110):
            if not 偏移894 or 偏移894 >= 关闭914:
                return 0
            return min(列866, (关闭914 - 偏移894) // 检查1110)
        self.s_n = fit(self.s_n, self.s_off, 4)
        self.t_n = fit(self.t_n, self.t_off, 4)
        self.p_n = fit(self.p_n, self.p_off, 12)
        self.m_n = fit(self.m_n, self.m_off, 8)
        self.c_n = fit(self.c_n, self.c_off, 32)
        self._scache = {}

    def string(self, 读取912):
        if 读取912 in self._scache:
            return self._scache[读取912]
        try:
            行745 = 句柄256(self.d, self.s_off + 读取912 * 4)
            步骤698, 值1062 = 步骤258(self.d, 行745)
            偏移1414 = self.d[值1062:值1062 + 步骤698].decode('utf-8', 'replace')
        except Exception:
            偏移1414 = ''
        self._scache[读取912] = 偏移1414
        return 偏移1414

    def type_name(self, 读取912):
        try:
            return self.string(句柄256(self.d, self.t_off + 读取912 * 4))
        except Exception:
            return ''

    def method_name(self, 读取912):
        try:
            return self.string(句柄256(self.d, self.m_off + 读取912 * 8 + 4))
        except Exception:
            return ''

    def method_ret(self, 读取912):
        try:
            偏移1494 = 区块255(self.d, self.m_off + 读取912 * 8 + 2)
            if 偏移1494 >= self.p_n:
                return ''
            return self.type_name(句柄256(self.d, self.p_off + 偏移1494 * 12 + 4))
        except Exception:
            return ''

    def stub_kind(self, 读取912, default=None):
        条目693 = self.method_ret(读取912)
        if not 条目693:
            return default
        if 条目693 == 'V':
            return 'void'
        if 条目693 == 'Z':
            return 'true'
        if 条目693 in ('J', 'D'):
            return 'wide'
        if 条目693 in ('I', 'S', 'B', 'C', 'F'):
            return 'zero'
        return 'null'

    def find_class(self, 映射852):
        limit = min(self.c_n, 400000)
        for 读取912 in range(limit):
            键863 = self.c_off + 读取912 * 32
            try:
                if self.type_name(句柄256(self.d, 键863)) == 映射852:
                    return 键863
            except Exception:
                return None
        return None
读取312 = {'void': b'\x0e\x00', 'true': b'\x12\x10\x0f\x00', 'false': b'\x12\x00\x0f\x00', 'zero': b'\x12\x00\x0f\x00', 'wide': b'\x16\x00\x00\x00\x10\x00', 'null': b'\x12\x00\x11\x00'}

def 打开313(计数805):
    try:
        sig = hashlib.sha1(bytes(计数805[32:])).digest()
        计数805[12:32] = sig
        缓存1443 = zlib.adler32(bytes(计数805[12:])) & 4294967295
        struct.pack_into('<I', 计数805, 8, 缓存1443)
        return True
    except Exception:
        return False
关闭314 = 12
构建315 = {1: 4, 2: 4, 3: 12, 4: 8, 5: 8, 6: 32, 7: 4, 8: 8}
解析316 = frozenset((0, 1, 2, 3, 4, 5, 6, 7, 8, 4096, 4097, 4098, 4099, 8193, 8198))
扫描317 = 6
修补318 = 8192
报告319 = 8193
变量320 = {0: 'header', 1: 'string_ids', 2: 'type_ids', 3: 'proto_ids', 4: 'field_ids', 5: 'method_ids', 6: 'class_defs', 7: 'call_site_ids', 8: 'method_handles', 4096: 'map_list', 4097: 'type_lists', 4098: 'annotation_set_refs', 4099: 'annotation_sets', 8192: 'class_data', 8193: 'code_items', 8194: 'string_data', 8195: 'debug_info', 8196: 'annotations', 8197: 'encoded_arrays', 8198: 'annotation_directories'}
参数321 = {'failures': [], 'rejected': []}

def 结果322(行785, 列786):
    节点857 = 0
    打开1073 = 0
    while 列786 < len(行785):
        映射692 = 行785[列786]
        列786 += 1
        节点857 |= (映射692 & 127) << 打开1073
        打开1073 += 7
        if not 映射692 & 128:
            if 打开1073 < 64 and 映射692 & 64:
                节点857 -= 1 << 打开1073
            return (节点857, 列786)
        if 打开1073 > 35:
            break
    return (节点857, 列786)

def 缓存323(行785, 行745):
    if 行745 < 0 or 行745 + 16 > len(行785):
        return None
    写入1111 = 区块255(行785, 行745 + 6)
    字节867 = 句柄256(行785, 行745 + 12)
    值1062 = 行745 + 16 + 字节867 * 2
    if 值1062 > len(行785):
        return None
    if not 写入1111:
        return 值1062
    if 字节867 & 1:
        值1062 += 2
    值1062 += 写入1111 * 8
    if 值1062 >= len(行785):
        return None
    列866, 值1062 = 步骤258(行785, 值1062)
    if 列866 > 65536:
        return None
    for 读取1112 in range(列866):
        关闭914, 值1062 = 结果322(行785, 值1062)
        for 读取1112 in range(abs(关闭914)):
            读取1112, 值1062 = 步骤258(行785, 值1062)
            读取1112, 值1062 = 步骤258(行785, 值1062)
        if 关闭914 <= 0:
            读取1112, 值1062 = 步骤258(行785, 值1062)
        if 值1062 > len(行785):
            return None
    return 值1062

def 索引324(行785, 行745):
    值1062 = 行745
    索引1444, 值1062 = 步骤258(行785, 值1062)
    计数1445, 值1062 = 步骤258(行785, 值1062)
    路径1446, 值1062 = 步骤258(行785, 值1062)
    列表1447, 值1062 = 步骤258(行785, 值1062)
    for 读取1112 in range(索引1444 + 计数1445):
        读取1112, 值1062 = 步骤258(行785, 值1062)
        读取1112, 值1062 = 步骤258(行785, 值1062)
    for 读取1112 in range(路径1446 + 列表1447):
        读取1112, 值1062 = 步骤258(行785, 值1062)
        读取1112, 值1062 = 步骤258(行785, 值1062)
        读取1112, 值1062 = 步骤258(行785, 值1062)
    if 值1062 <= 行745 or 值1062 > len(行785):
        return None
    return 值1062

def 计数325(行785):
    if len(行785) < 112 or 行785[:4] != b'dex\n':
        return None
    打开1113 = 句柄256(行785, 52)
    if 打开1113 < 112 or 打开1113 + 4 > len(行785):
        return None
    步骤698 = 句柄256(行785, 打开1113)
    if 步骤698 == 0 or 步骤698 > 1024 or 打开1113 + 4 + 步骤698 * 关闭314 > len(行785):
        return None
    文本708 = []
    for 读取912 in range(步骤698):
        键863 = 打开1113 + 4 + 读取912 * 关闭314
        文本708.append((句柄256(行785, 键863 + 8), 区块255(行785, 键863), 句柄256(行785, 键863 + 4)))
    return 文本708

def 路径326(行785):
    行785 = bytes(行785)
    关闭1114 = []

    def bad(句柄776):
        关闭1114.append(('bad', 句柄776))

    def warn(句柄776):
        关闭1114.append(('warn', 句柄776))
    if len(行785) < 112 or 行785[:4] != b'dex\n':
        return [('bad', 'not a dex file')]
    if 句柄256(行785, 32) != len(行785):
        bad('header file_size is %d but the file is %d byte(s)' % (句柄256(行785, 32), len(行785)))
    if 句柄256(行785, 36) != 112:
        bad('header_size is not 0x70')
    if 句柄256(行785, 40) != 305419896:
        bad('bad endian_tag')
    构建795 = 计数325(行785)
    if 构建795 is None:
        return 关闭1114 + [('bad', 'map_list unreadable')]
    if 构建795[0][1] != 0 or 构建795[0][0] != 0:
        bad('map_list does not begin with the header at offset 0')
    构建1115 = -1
    for 行745, 数据1448, 列866 in 构建795:
        name = 变量320.get(数据1448, '0x%04x' % 数据1448)
        if 行745 < 构建1115 and (not (数据1448 == 0 and 行745 == 0)):
            bad('%s at 0x%x is out of order' % (name, 行745))
        构建1115 = max(构建1115, 行745)
        if 行745 >= len(行785):
            bad('%s offset 0x%x is past the end of the file' % (name, 行745))
        elif 数据1448 in 解析316 and 数据1448 != 0 and 行745 % 4:
            bad('%s is not 4 byte aligned (0x%x)' % (name, 行745))
    解析1116 = {}
    扫描1117 = {}
    for 行745, 数据1448, 列866 in 构建795:
        关闭914 = 构建315.get(数据1448)
        if 关闭914 is None or not 列866:
            continue
        end = 行745 + 列866 * 关闭914
        if end > len(行785):
            bad('%s overruns the file (%d item(s))' % (变量320.get(数据1448, '0x%04x' % 数据1448), 列866))
            continue
        解析1116[行745] = end
    for 行745, 数据1448, 列866 in 构建795:
        if 数据1448 == 报告319 and 列866:
            值1062 = 行745
            标记1610 = True
            for 读取912 in range(列866):
                end = 缓存323(行785, 值1062)
                if end is None or end <= 值1062:
                    warn('code_item #%d at 0x%x could not be walked · the section is left unchecked' % (读取912, 值1062))
                    标记1610 = False
                    break
                值1062 = end
            if 标记1610:
                扫描1117[行745] = 值1062
        elif 数据1448 == 修补318 and 列866:
            列1706 = next((节点697 for 节点697 in 构建795 if 节点697[1] == 扫描317), None)
            if not 列1706 or not 列1706[2]:
                continue
            变量960 = 行745
            标记1610 = True
            for 读取912 in range(列1706[2]):
                目标1141 = 句柄256(行785, 列1706[0] + 读取912 * 32 + 24)
                if not 目标1141:
                    continue
                end = 索引324(行785, 目标1141)
                if end is None:
                    标记1610 = False
                    break
                变量960 = max(变量960, end)
            if 标记1610:
                扫描1117[行745] = 变量960
    写入991 = sorted({节点697[0] for 节点697 in 构建795})
    修补1118 = {节点697[0]: 节点697[1] for 节点697 in 构建795}
    for 状态1449, 偏移974 in (('bad', 解析1116), ('warn', 扫描1117)):
        for 行745 in sorted(偏移974):
            if 状态1449 == 'warn' and 行745 in 解析1116:
                continue
            end = 偏移974[行745]
            字节1507 = next((节点697 for 节点697 in 写入991 if 节点697 > 行745), None)
            if 字节1507 is None:
                continue
            if end > 字节1507:
                表704 = '%s at 0x%x runs %d byte(s) into the next section at 0x%x' % (变量320.get(修补1118.get(行745), '0x%x' % 行745), 行745, end - 字节1507, 字节1507)
                bad(表704) if 状态1449 == 'bad' else warn(表704)
                continue
            队列1611 = [值1062 for 值1062 in range(end, min(字节1507, len(行785))) if 行785[值1062]]
            if 队列1611:
                表704 = 'non-zero padding before %s at 0x%x · %d leftover byte(s), first 0x%02x at 0x%x' % (变量320.get(修补1118.get(字节1507), '0x%x' % 字节1507), 字节1507, len(队列1611), 行785[队列1611[0]], 队列1611[0])
                bad(表704) if 状态1449 == 'bad' else warn(表704)
    if zlib.adler32(行785[12:]) & 4294967295 != 句柄256(行785, 8):
        bad('header checksum mismatch · bytes were written after the header was sealed')
    if hashlib.sha1(行785[32:]).digest() != 行785[12:32]:
        bad('header sha1 mismatch · bytes were written after the header was sealed')
    return 关闭1114

def 列表327(键743):
    report = []
    try:
        with zipfile.ZipFile(str(键743)) as 键1023:
            for name in sorted((步骤698 for 步骤698 in 键1023.namelist() if re.match('classes\\d*\\.dex$', 步骤698))):
                参数721 = 键1023.read(name)
                report.append((name, len(参数721), 路径326(参数721)))
    except Exception as 修补958:
        report.append(('<archive>', 0, [('bad', 'cannot read the archive · ' + str(修补958))]))
    return report

def 数据328(键743):
    report = 列表327(键743)
    if not report:
        键63.warn('no classes*.dex found · nothing to audit')
        return False
    变量1120 = 0
    for name, 关闭914, 关闭1114 in report:
        读取1432 = [句柄776 for 节点697, 句柄776 in 关闭1114 if 节点697 == 'bad']
        标记1450 = [句柄776 for 节点697, 句柄776 in 关闭1114 if 节点697 == 'warn']
        if 读取1432:
            变量1120 += 1
            键63.bad('%s · %s' % (name, 读取1432[0]))
            for 句柄776 in 读取1432[1:3]:
                键63.info('  ' + 句柄776)
            键63.info('  android drops this whole dex at load time · every class inside it disappears')
        elif 标记1450:
            键63.warn('%s · %s' % (name, 标记1450[0]))
    if 变量1120:
        键63.bad('%d of %d dex file(s) would be rejected by ART' % (变量1120, len(report)))
        键63.info('a rejected dex is invisible at install time · it only shows up as ClassNotFoundException at launch')
        return False
    键63.ok('%d dex file(s) pass the structural audit' % len(report))
    return True

def 状态329(键743):
    队列1451, info = 区块615(键743)
    if not 队列1451:
        键63.warn('manifest unreadable · the applied flags cannot be confirmed')
        return
    参数1121 = 报告279(队列1451)
    if not 参数1121.valid or 参数1121.pool is None or (not 参数1121.pool.items) or (not 参数1121.attrs):
        键63.warn('binary manifest could not be decoded by this parser · flags unknown')
        键63.info("do not read the next lines as 'absent': this file uses a pool layout the parser misses")
        return
    if not info:
        键63.warn('manifest unreadable · the applied flags cannot be confirmed')
        return
    键63.kv('manifest flags', ' · '.join(['debuggable=' + ('true' if info.get('debuggable') else 'false'), 'cleartext=' + ('true' if info.get('cleartext') else 'false'), 'netsec=' + ('present' if info.get('netsec') else 'absent')]))
    if not info.get('netsec'):
        键63.warn('no networkSecurityConfig in the final manifest · android falls back to the platform trust store')
    if not info.get('debuggable'):
        键63.info("debuggable is not set · a 'manifest hardened' claim would be false here")

def 标记330(参数721, 行745, 行705):
    if 行745 <= 0 or 行745 + 16 > len(参数721):
        return False
    try:
        映射1452 = 区块255(参数721, 行745)
        值1142 = 区块255(参数721, 行745 + 2)
        字节867 = 句柄256(参数721, 行745 + 12)
    except Exception:
        return False
    结果1122 = 读取312.get(行705)
    if not 结果1122 or 映射1452 == 0:
        return False
    名字1109 = len(结果1122) // 2
    if 字节867 < 名字1109:
        return False
    键863 = 行745 + 16
    if 键863 + 字节867 * 2 > len(参数721):
        return False
    缓存1123 = 值1142 if 行705 == 'void' else max(值1142 + 1, 1)
    if 缓存1123 > 65535:
        return False
    struct.pack_into('<HHH', 参数721, 行745, 缓存1123, 值1142, 0)
    参数721[键863:键863 + len(结果1122)] = 结果1122
    if 名字1109 < 字节867:
        参数721[键863 + len(结果1122):键863 + 字节867 * 2] = b'\x00\x00' * (字节867 - 名字1109)
    return True

def 队列331(参数721, 行745, 行705):
    结果1122 = 读取312.get(行705)
    if not 结果1122 or 行745 <= 0 or 行745 + 16 > len(参数721):
        return False
    字节867 = 句柄256(参数721, 行745 + 12)
    名字1109 = len(结果1122) // 2
    if 字节867 < 名字1109:
        return False
    键863 = 行745 + 16
    end = 键863 + 字节867 * 2
    if end > len(参数721):
        return False
    if bytes(参数721[键863:键863 + len(结果1122)]) != 结果1122:
        return False
    return bytes(参数721[键863 + len(结果1122):end]) == b'\x00\x00' * (字节867 - 名字1109)

def 映射332(参数721, 路径806):
    区块815 = 写入311(参数721)
    if not 区块815.ok:
        return (bytearray(参数721), [])
    计数805 = bytearray(参数721)
    步骤978 = []
    for 映射852, 条目1453, 行705 in 路径806:
        名字829 = 区块815.find_class(映射852)
        if 名字829 is None:
            continue
        目标1141 = 句柄256(计数805, 名字829 + 24)
        if not 目标1141:
            continue
        值1062 = 目标1141
        try:
            索引1444, 值1062 = 步骤258(计数805, 值1062)
            计数1445, 值1062 = 步骤258(计数805, 值1062)
            路径1446, 值1062 = 步骤258(计数805, 值1062)
            列表1447, 值1062 = 步骤258(计数805, 值1062)
            for 读取1112 in range(索引1444):
                读取1112, 值1062 = 步骤258(计数805, 值1062)
                读取1112, 值1062 = 步骤258(计数805, 值1062)
            for 读取1112 in range(计数1445):
                读取1112, 值1062 = 步骤258(计数805, 值1062)
                读取1112, 值1062 = 步骤258(计数805, 值1062)
            for 列866 in (路径1446, 列表1447):
                结果882 = 0
                for 读取1112 in range(列866):
                    文本1108, 值1062 = 步骤258(计数805, 值1062)
                    结果882 += 文本1108
                    读取1112, 值1062 = 步骤258(计数805, 值1062)
                    栈819, 值1062 = 步骤258(计数805, 值1062)
                    if not 栈819:
                        continue
                    if 区块815.method_name(结果882) != 条目1453:
                        continue
                    解析1756 = 区块815.stub_kind(结果882, 行705)
                    标记1010 = 缓存323(计数805, 栈819)
                    计数1005 = bytes(计数805[栈819:标记1010]) if 标记1010 else None
                    if not 标记330(计数805, 栈819, 解析1756):
                        continue
                    结果1202 = 缓存323(计数805, 栈819)
                    if 标记1010 is None or 结果1202 != 标记1010 or (not 队列331(计数805, 栈819, 解析1756)):
                        if 计数1005:
                            计数805[栈819:标记1010] = 计数1005
                        参数321['failures'].append((映射852, 条目1453, 栈819))
                        continue
                    步骤978.append((映射852, 条目1453, 栈819, 解析1756))
        except Exception:
            continue
    if 步骤978:
        打开313(计数805)
    return (计数805, 步骤978)
条目333 = [('Ljavax/net/ssl/X509TrustManager;', 'checkServerTrusted', 'void'), ('Ljavax/net/ssl/X509TrustManager;', 'checkClientTrusted', 'void'), ('Landroid/webkit/WebViewClient;', 'onReceivedSslError', 'void'), ('Landroid/webkit/WebViewClient;', 'onReceivedError', 'void'), ('Landroid/webkit/WebViewClient;', 'onReceivedClientCertRequest', 'void'), ('Landroid/security/NetworkSecurityPolicy;', 'isCleartextTrafficPermitted', 'true'), ('Landroid/net/http/X509TrustManagerExtensions;', 'checkServerTrusted', 'void'), ('Ljava/security/cert/X509Certificate;', 'checkValidity', 'void')]
偏移334 = {'checkTrustedRecursive': 'void', 'checkTrustAnchor': 'void', 'checkServerTrusted': 'void', 'checkClientTrusted': 'void', 'verifyHostname': 'true', 'verifyHost': 'true', 'verifyCertificateChain': 'void', 'checkValidity': 'void', 'onReceivedClientCertRequest': 'void'}
区块335 = {'allowAccess': 'true', 'connectToLicensingService': 'void', 'retryOrThrow': 'void', 'dontAllow': 'void', 'isLicensed': 'true', 'verifyLicense': 'true'}

def 句柄336(键743):
    路径806 = list(条目333)
    try:
        with zipfile.ZipFile(键743) as 键1023:
            for name in 键1023.namelist():
                if not re.match('classes\\d*\\.dex$', name):
                    continue
                区块815 = 写入311(键1023.read(name))
                if not 区块815.ok:
                    continue
                for 映射852 in 区块375(区块815, 250000):
                    if not 映射852.startswith('L'):
                        continue
                    关闭1074 = 映射852.lower()
                    if 'hostnameverifier' in 关闭1074:
                        路径806.append((映射852, 'verify', 'true'))
                        路径806.append((映射852, 'verifyHostname', 'true'))
                    elif 'certificatepinner' in 关闭1074:
                        路径806.append((映射852, 'check', 'void'))
                    elif 'chaincleaner' in 关闭1074:
                        路径806.append((映射852, 'clean', 'void'))
                    elif 'trustmanager' in 关闭1074:
                        路径806.append((映射852, 'checkServerTrusted', 'void'))
                        路径806.append((映射852, 'checkClientTrusted', 'void'))
                        路径806.append((映射852, 'checkTrustedRecursive', 'void'))
                    elif 'cronet' in 关闭1074 or 'certverifier' in 关闭1074:
                        路径806.append((映射852, 'verifyCertificateChain', 'void'))
    except Exception:
        pass
    return 路径806

def 节点337(键743, 文本708, 路径806, 列表807=None):
    键1103 = []
    参数321['failures'] = []
    参数321['rejected'] = []
    try:
        with zipfile.ZipFile(键743) as 名字1429:
            修补798 = {}
            for name in 名字1429.namelist():
                if not re.match('classes\\d*\\.dex$', name):
                    continue
                参数721 = 名字1429.read(name)
                计数805, 步骤978 = 映射332(参数721, 路径806)
                if 列表807:
                    栈1779, 源1780 = 偏移374(bytes(计数805), 列表807)
                    if 源1780:
                        计数805 = 栈1779
                        步骤978 = list(步骤978) + list(源1780)
                if 步骤978:
                    扫描1757 = {句柄776 for 节点697, 句柄776 in 路径326(bytes(参数721)) if 节点697 == 'bad'}
                    行1105 = {句柄776 for 节点697, 句柄776 in 路径326(bytes(计数805)) if 节点697 == 'bad'}
                    索引1004 = 行1105 - 扫描1757
                    if 索引1004:
                        参数321['rejected'].append((name, sorted(索引1004)[0]))
                        步骤978 = []
                    else:
                        修补798[name] = bytes(计数805)
                        键1103.extend(((name,) + 解析956 for 解析956 in 步骤978))
            if not 修补798:
                return (False, 键1103)
            with zipfile.ZipFile(文本708, 'w') as 检查1430:
                for 区块1415 in 名字1429.infolist():
                    if 区块1415.filename.upper().startswith('META-INF/') and 区块1415.filename.upper().endswith(('.SF', '.RSA', '.DSA', '.EC', '.MF')):
                        continue
                    参数761 = 修补798.get(区块1415.filename)
                    if 参数761 is None:
                        参数761 = 名字1429.read(区块1415.filename)
                    状态1609 = zipfile.ZipInfo(区块1415.filename, date_time=区块1415.date_time)
                    状态1609.compress_type = 区块1415.compress_type
                    状态1609.external_attr = 区块1415.external_attr
                    状态1609.internal_attr = 区块1415.internal_attr
                    状态1609.create_system = 区块1415.create_system
                    检查1430.writestr(状态1609, 参数761)
        return (True, 键1103)
    except Exception:
        if Path(文本708).exists():
            Path(文本708).unlink(missing_ok=True)
        return (False, 键1103)

class 步骤338:

    def __init__(self, 参数721):
        self.raw = 参数721
        self.strings = []
        self.chunks = []
        self.pool_index = None
        self.ok = False
        self._parse()

    def _parse(self):
        行785 = self.raw
        if len(行785) < 16 or 区块255(行785, 0) != 3:
            return
        self.ok = True
        行745 = 区块255(行785, 2)
        列986 = 0
        while 行745 + 8 <= len(行785) and 列986 < 400000:
            列986 += 1
            写入1351 = 区块255(行785, 行745)
            读取1352 = 句柄256(行785, 行745 + 4)
            if 读取1352 < 8:
                break
            self.chunks.append([写入1351, 行785[行745:行745 + 读取1352]])
            行745 += 读取1352
        for 读取912, (写入1351, 表744) in enumerate(self.chunks):
            if 写入1351 == 1:
                self.pool_index = 读取912
                self.strings = list(栈259(表744, 0).items)
                break

    def intern(self, 标记730):
        try:
            return self.strings.index(标记730)
        except ValueError:
            self.strings.append(标记730)
            return len(self.strings) - 1

    def build_pool(self):
        偏移1454 = b''
        参数721 = b''
        键863 = 28 + 4 * len(self.strings)
        for 节点697 in self.strings:
            偏移1454 += struct.pack('<I', len(参数721))
            句柄1416 = 节点697.encode('utf-8')
            映射1612 = len(节点697.encode('utf-16-le')) // 2
            参数721 += 节点257(映射1612) + 节点257(len(句柄1416)) + 句柄1416 + b'\x00'
        while (键863 + len(参数721)) % 4:
            参数721 += b'\x00'
        关闭914 = 键863 + len(参数721)
        return struct.pack('<HHIIIIII', 1, 28, 关闭914, len(self.strings), 0, 256, 键863, 0) + 偏移1454 + 参数721

    def patch_application(self, 偏移734):
        键1103 = []
        for 读取912, (写入1351, 表744) in enumerate(self.chunks):
            if 写入1351 != 258:
                continue
            文本748 = 句柄256(表744, 20)
            if not 0 <= 文本748 < len(self.strings) or self.strings[文本748] != 'application':
                continue
            字节1707, 句柄1456 = self._apply(表744, 偏移734)
            if 句柄1456:
                self.chunks[读取912][1] = 字节1707
                键1103.extend(句柄1456)
            break
        return 键1103

    def _apply(self, 表744, 偏移734):
        键863 = 16
        列866 = 区块255(表744, 键863 + 12)
        start = 区块255(表744, 键863 + 8) or 20
        关闭914 = 区块255(表744, 键863 + 10) or 20
        文本708 = bytearray(表744)
        区块1455 = {}
        for 读取912 in range(列866):
            队列691 = 键863 + start + 读取912 * 关闭914
            结果1602 = 句柄256(文本708, 队列691 + 4)
            if 0 <= 结果1602 < len(self.strings):
                区块1455[self.strings[结果1602]] = 队列691
        句柄1456 = []
        节点1457 = []
        for name, 参数921, 标记730 in 偏移734:
            if name in 区块1455:
                队列691 = 区块1455[name]
                字节747, 修补1758 = self._fields(参数921, 标记730)
                struct.pack_into('<H', 文本708, 队列691 + 12, 8)
                文本708[队列691 + 14] = 0
                文本708[队列691 + 15] = 参数921
                struct.pack_into('<I', 文本708, 队列691 + 8, 字节747)
                struct.pack_into('<I', 文本708, 队列691 + 16, 修补1758)
                句柄1456.append(name)
            else:
                节点1457.append((name, 参数921, 标记730))
        if 节点1457:
            列表847 = b''
            for name, 参数921, 标记730 in 节点1457:
                结果1602 = self.intern(name)
                字节747, 修补1758 = self._fields(参数921, 标记730)
                列表847 += struct.pack('<IIIHBBI', 4294967295, 结果1602, 字节747, 8, 0, 参数921, 修补1758)
                句柄1456.append(name)
            文本948 = 键863 + start + 列866 * 关闭914
            文本708 = bytearray(bytes(文本708[:文本948]) + 列表847 + bytes(文本708[文本948:]))
            struct.pack_into('<H', 文本708, 键863 + 12, 列866 + len(节点1457))
            struct.pack_into('<I', 文本708, 4, len(文本708))
        return (bytes(文本708), 句柄1456)

    def _fields(self, 参数921, 标记730):
        if 参数921 == 3:
            区块815 = self.intern(str(标记730))
            return (区块815, 区块815)
        try:
            return (4294967295, int(标记730))
        except Exception:
            return (4294967295, 0)

    def serialize(self):
        if not self.ok:
            return None
        变量760 = []
        for 读取912, (写入1351, 表744) in enumerate(self.chunks):
            if 读取912 == self.pool_index:
                变量760.append(self.build_pool())
            else:
                变量760.append(表744)
        列表847 = b''.join(变量760)
        return struct.pack('<HHI', 3, 8, 8 + len(列表847)) + 列表847

def 栈339(参数721, 数据808):
    列946 = 步骤338(参数721)
    if not 列946.ok or 列946.pool_index is None:
        return (None, [])
    键1103 = 列946.patch_application(数据808)
    if not 键1103:
        return (None, [])
    文本708 = 列946.serialize()
    return (文本708, 键1103)

def 源340(参数721):
    索引1124 = {1: 4, 2: 4, 3: 12, 4: 8, 5: 8, 6: 32, 7: 4, 8: 8}
    if len(参数721) < 112 or 参数721[:4] != b'dex\n':
        return (参数721, 0)
    try:
        打开1113 = struct.unpack_from('<I', 参数721, 52)[0]
        步骤1458 = struct.unpack_from('<I', 参数721, 打开1113)[0]
        if 步骤1458 == 0 or 步骤1458 > 1024:
            return (参数721, 0)
        构建795 = []
        for 读取912 in range(步骤1458):
            键863 = 打开1113 + 4 + 读取912 * 12
            数据1448 = struct.unpack_from('<H', 参数721, 键863)[0]
            列866 = struct.unpack_from('<I', 参数721, 键863 + 4)[0]
            行745 = struct.unpack_from('<I', 参数721, 键863 + 8)[0]
            构建795.append((行745, 数据1448, 列866))
        构建795.sort()
        栈1459 = {}
        for 读取912 in range(len(构建795) - 1):
            栈1459[构建795[读取912][0]] = 构建795[读取912 + 1][0]
        文本708 = bytearray(参数721)
        缓存1363 = 0
        for 行745, 数据1448, 列866 in 构建795:
            条目1613 = 索引1124.get(数据1448)
            if 条目1613 is None or 列866 == 0:
                continue
            end = 行745 + 列866 * 条目1613
            字节1507 = 栈1459.get(行745)
            if 字节1507 is None or end > 字节1507 or end >= len(文本708):
                continue
            for 值1062 in range(end, min(字节1507, len(文本708))):
                if 文本708[值1062] != 0:
                    文本708[值1062] = 0
                    缓存1363 += 1
        if 缓存1363:
            文本708[12:32] = hashlib.sha1(bytes(文本708[32:])).digest()
            struct.pack_into('<I', 文本708, 8, zlib.adler32(bytes(文本708[12:])) & 4294967295)
            标记1010 = len([句柄776 for 节点697, 句柄776 in 路径326(bytes(参数721)) if 节点697 == 'bad'])
            结果1202 = len([句柄776 for 节点697, 句柄776 in 路径326(bytes(文本708)) if 节点697 == 'bad'])
            if 结果1202 > 标记1010:
                return (参数721, 0)
        return (bytes(文本708), 缓存1363)
    except Exception:
        return (参数721, 0)

def 目标341(构建755, 写入751):
    import zipfile as _zf, re as _re, struct as _st
    try:
        参数1281 = set()
        with _zf.ZipFile(str(构建755)) as 键1023:
            for name in 键1023.namelist():
                if not _re.match('classes\\d*\\.dex$', name):
                    continue
                try:
                    报告1759 = 队列611(键1023.read(name))
                    if 报告1759:
                        参数1281.update(报告1759)
                except Exception:
                    pass
        if not 参数1281:
            return 0

        def _norm(cls):
            映射1132 = cls.strip()
            if 映射1132.startswith('L') and 映射1132.endswith(';'):
                映射1132 = 映射1132[1:-1]
            return 映射1132.replace('/', '.')
        行1385 = {_norm(映射1132) for 映射1132 in 参数1281}
        with _zf.ZipFile(str(构建755)) as 键1023:
            if 'AndroidManifest.xml' not in 键1023.namelist():
                return 0
            偏移1614 = 键1023.read('AndroidManifest.xml')
        数据1208 = ''
        try:
            info = 变量280(偏移1614)
            if info:
                值1062 = info.get('package', '')
                if 值1062 and 值1062 != '?':
                    数据1208 = 值1062
        except Exception:
            pass
        try:
            表904 = 报告279(偏移1614)
            if not 表904.valid:
                return 0
        except Exception:
            return 0
        源1460 = set()
        目标1461 = {'provider', 'service', 'receiver', 'activity', 'activity-alias'}
        for 状态929 in 表904.walk:
            if 状态929.get('kind') != 'start':
                continue
            映射732 = 状态929.get('name', '').split('}')[-1] if '}' in 状态929.get('name', '') else 状态929.get('name', '')
            if 映射732 not in 目标1461:
                continue
            偏移734 = dict(状态929.get('attrs', []))
            值1462 = None
            for 名字989, 步骤818 in 偏移734.items():
                条目733 = 名字989.split('}')[-1] if '}' in 名字989 else 名字989
                if 条目733 == 'name':
                    值1462 = 步骤818
                    break
            if not 值1462:
                continue
            if 值1462.startswith('.'):
                值1462 = 数据1208 + 值1462
            elif '.' not in 值1462 and 数据1208:
                值1462 = 数据1208 + '.' + 值1462
            if 值1462 not in 行1385:
                源1460.add(值1462)
        if not 源1460:
            return 0
        try:
            区块1615 = 解析676(表904)
        except Exception:
            return 0
        if not 区块1615:
            return 0
        句柄1056 = 0
        for 值1462 in 源1460:
            句柄1616 = 值1462.split('.')[-1]
            节点1617 = 值1462.replace('.', '\\.')
            步骤1618 = 句柄1616.replace('.', '\\.')
            for 计数725 in ['<(?:provider|service|receiver|activity|activity-alias)(?:\\s[^>]*)?(?:android:name|name)="' + _re.escape(值1462) + '"[^>]*(?:/>|>.*?</(?:provider|service|receiver|activity|activity-alias)>)']:
                结果1722, 步骤698 = _re.subn(计数725, '', 区块1615, flags=_re.DOTALL)
                if 步骤698:
                    区块1615 = 结果1722
                    句柄1056 += 步骤698
        if not 句柄1056:
            return 0
        try:
            栈1619 = 列表687(区块1615)
        except Exception as 计数1125:
            键63.warn('manifest re-encode failed · ' + str(计数1125))
            return 0
        扫描797 = Path(str(构建755) + '.prune')
        with _zf.ZipFile(str(构建755)) as 名字1429, _zf.ZipFile(str(扫描797), 'w', allowZip64=True) as 检查1430:
            for info in 名字1429.infolist():
                参数761 = 栈1619 if info.filename == 'AndroidManifest.xml' else 名字1429.read(info.filename)
                状态1609 = _zf.ZipInfo(info.filename, date_time=info.date_time)
                状态1609.compress_type = info.compress_type
                状态1609.external_attr = info.external_attr
                状态1609.internal_attr = info.internal_attr
                状态1609.create_system = info.create_system
                检查1430.writestr(状态1609, 参数761)
        import os as _os
        _os.replace(str(扫描797), str(构建755))
        return 句柄1056
    except Exception as 计数1125:
        键63.warn('manifest prune skipped · ' + str(计数1125))
        return 0

def 值342(路径766, 列表767, 映射772, args):
    键63.head('surgical engine', 字节27)
    键63.info('no apktool, no aapt2 · direct dex and manifest editing')
    路径806 = 句柄336(列表767)
    路径1126 = {步骤698: 'true' for 步骤698 in 句柄136}
    路径1126.update({步骤698: 'false' for 步骤698 in 节点137})
    路径1126.update(偏移334)
    if getattr(args, 'mode', '') in ('signature', 'full', 'ssl') or getattr(args, 'remove_license', False):
        路径1126.update(区块335)
    if getattr(args, '路径806', None):
        检查1590, 写入1591, 关闭1114 = 路径366(args.targets)
        for 字节1387 in 关闭1114:
            键63.warn(字节1387)
        路径806.extend(检查1590)
        路径1126.update(写入1591)
        键63.kv('user targets', '%d class-bound · %d name-bound' % (len(检查1590), len(写入1591)))
    键63.kv('targets', '%d class-bound · %d name-bound' % (len(路径806), len(路径1126)))
    打开953 = Path(路径766.work) / 'surgery.apk'
    ok, 键1103 = 节点337(列表767, 打开953, 路径806, 路径1126)
    if ok:
        键63.ok('%d method(s) rewritten across %d dex file(s)' % (len(键1103), len({映射1132[0] for 映射1132 in 键1103})))
        for name, 映射852, 条目1453, 行745, 行705 in 键1103[:12]:
            键63.bullet('%s · %s · %s' % (name, 映射852.split('/')[-1].rstrip(';'), 条目1453))
        if len(键1103) > 12:
            键63.info('… %d more' % (len(键1103) - 12))
    else:
        键63.warn('no method matched · copying the archive unchanged')
        键63.warn('the output is the ORIGINAL app, unmodified · nothing was neutralised')
        键63.info('check the target list above: the methods it looked for are not in this build')
        shutil.copy2(列表767, 打开953)
    数据808 = [('debuggable', 18, 4294967295), ('usesCleartextTraffic', 18, 4294967295)]
    try:
        with zipfile.ZipFile(打开953) as 键1023:
            索引884 = 区块615(键1023)[0]
        源1620, 栈979 = 栈339(索引884, 数据808)
    except Exception:
        源1620, 栈979 = (None, [])
    if 源1620:
        扫描797 = Path(路径766.work) / 'surgery_manifest.apk'
        with zipfile.ZipFile(打开953) as 名字1429, zipfile.ZipFile(扫描797, 'w') as 检查1430:
            for 区块1415 in 名字1429.infolist():
                参数761 = 源1620 if 区块1415.filename == 'AndroidManifest.xml' else 名字1429.read(区块1415.filename)
                状态1609 = zipfile.ZipInfo(区块1415.filename, date_time=区块1415.date_time)
                状态1609.compress_type = 区块1415.compress_type
                状态1609.external_attr = 区块1415.external_attr
                状态1609.internal_attr = 区块1415.internal_attr
                状态1609.create_system = 区块1415.create_system
                检查1430.writestr(状态1609, 参数761)
        os.replace(扫描797, 打开953)
        键63.ok('manifest edited in place · ' + ', '.join(栈979))
    else:
        键63.info('manifest already carries the target flags')
    键1463, 表1464 = 列表167(打开953)
    if 键1463 == 'replaced':
        键63.ok('network security config rewritten in the archive · ' + 表1464)
    elif 键1463 == 'unchanged':
        键63.ok('network security config already trusts user CAs · ' + 表1464)
    elif 键1463 == 'absent':
        键63.warn('no network security config to replace · ' + 表1464)
        键63.info('with none, android trusts system CAs only · a user CA is rejected')
    else:
        键63.warn('netsec injection failed · ' + 表1464)
    for 行1465, 列1466 in 路径166(打开953, 路径766.work, getattr(args, 'flutter_engine', None)):
        if 列1466.hits:
            for 句柄1576, 文本1708, 名字1709, _st in 列1466.names:
                if _st != 'patched':
                    continue
                键63.ok('%s · %s @0x%x · returns %d' % (行1465, 文本1708, 句柄1576, 名字1709))
                路径766.records.append({'file': 行1465, 'offset': hex(句柄1576), 'arch': 列1466.arch, 'kind': 'tls-verify', 'ret': 名字1709, 'fn': 文本1708})
        elif 列1466.already:
            键63.info('%s · engine already patched' % 行1465)
        elif getattr(列1466, 'error', None):
            键63.warn('%s · %s' % (行1465, 列1466.error))
    for name, 字节1467 in 参数321.get('rejected', []):
        键63.bad('%s would not load after patching · kept the original bytes' % name)
        键63.info('  ' + 字节1467)
    for 映射852, 条目1453, 行745 in 参数321.get('failures', [])[:6]:
        键63.warn('patch skipped · %s · %s would have changed the item length' % (映射852.split('/')[-1].rstrip(';'), 条目1453))
    if not 数据328(打开953):
        文本1468 = {步骤698 for 步骤698, 条目1533, 值1062 in 列表327(列表767) if any((节点697 == 'bad' for 节点697, 读取1112 in 值1062))}
        名字1469 = {步骤698 for 步骤698, 条目1533, 值1062 in 列表327(打开953) if any((节点697 == 'bad' for 节点697, 读取1112 in 值1062))}
        if 名字1469 and 名字1469 <= 文本1468:
            键63.warn('the input dex was already rejected by ART · this build did not cause it')
        else:
            键63.bad('refusing to sign this build · the dex layout above crashes the app at launch')
            键63.info('artifact kept for inspection: ' + str(打开953))
            return (None, 'surgery')
    列表1127 = 目标341(打开953, 路径766.work)
    if 列表1127:
        键63.ok('pruned %d orphan manifest component(s)' % 列表1127)
    shutil.move(str(打开953), str(映射772))
    return (映射772, 'surgery')
键343 = {'fh': None, 'path': None}

def 表344(变量720=None):
    if 键343['fh']:
        return 键343['path']
    关闭794 = Path(变量720).expanduser() if 变量720 else HOME / ('arp-%s.log' % time.strftime('%Y%m%d-%H%M%S'))
    try:
        关闭794.parent.mkdir(parents=True, exist_ok=True)
        键343['fh'] = open(关闭794, 'w', encoding='utf-8', errors='replace')
        键343['path'] = 关闭794
        return 关闭794
    except Exception:
        return None

def 行345(行705, text):
    if not 键343['fh']:
        return
    try:
        解析796 = time.strftime('%H:%M:%S')
        键343['fh'].write('[%s] %-5s %s\n' % (解析796, 行705, text))
        键343['fh'].flush()
    except Exception:
        pass

def 列346():
    if 键343['fh']:
        try:
            键343['fh'].close()
        except Exception:
            pass
        键343['fh'] = None
字节347 = {110, 111, 112, 113, 114, 116, 117, 118, 119, 120}

def 文本348(参数721):
    区块815 = 写入311(参数721)
    if not 区块815.ok:
        return []
    数据1128 = []
    limit = min(区块815.c_n, 60000)
    for 读取912 in range(limit):
        名字829 = 区块815.c_off + 读取912 * 32
        映射852 = 区块815.type_name(句柄256(参数721, 名字829))
        目标1141 = 句柄256(参数721, 名字829 + 24)
        if not 目标1141:
            continue
        值1062 = 目标1141
        try:
            索引1444, 值1062 = 步骤258(参数721, 值1062)
            计数1445, 值1062 = 步骤258(参数721, 值1062)
            路径1446, 值1062 = 步骤258(参数721, 值1062)
            列表1447, 值1062 = 步骤258(参数721, 值1062)
            for 读取1112 in range(索引1444 + 计数1445):
                读取1112, 值1062 = 步骤258(参数721, 值1062)
                读取1112, 值1062 = 步骤258(参数721, 值1062)
            for 列866 in (路径1446, 列表1447):
                结果882 = 0
                for 读取1112 in range(列866):
                    文本1108, 值1062 = 步骤258(参数721, 值1062)
                    结果882 += 文本1108
                    读取1112, 值1062 = 步骤258(参数721, 值1062)
                    栈819, 值1062 = 步骤258(参数721, 值1062)
                    if not 栈819:
                        continue
                    步骤698 = 句柄256(参数721, 栈819 + 12)
                    键863 = 栈819 + 16
                    for 名字989 in range(min(步骤698, 20000)):
                        if 名字989 + 1 >= 步骤698:
                            break
                        目标861 = 区块255(参数721, 键863 + 名字989 * 2)
                        值862 = 目标861 & 255
                        if 值862 in 字节347:
                            索引1484 = 区块255(参数721, 键863 + (名字989 + 1) * 2)
                            if 索引1484 < 区块815.m_n:
                                数据1128.append((映射852, 区块815.method_name(结果882), 区块815.method_name(索引1484)))
        except Exception:
            continue
    return 数据1128
名字349 = re.compile('(CertificatePinner|TrustManager|HostnameVerifier|sslSocketFactory|X509TrustManager|pin-set|PublicKeyPinning)', re.I)

def 检查350(键743):
    句柄816 = {}
    状态1129 = set()
    try:
        with zipfile.ZipFile(键743) as 键1023:
            for name in 键1023.namelist():
                if re.match('classes\\d*\\.dex$', name):
                    参数721 = 键1023.read(name)
                    区块815 = 写入311(参数721)
                    if not 区块815.ok:
                        continue
                    for 读取912 in range(min(区块815.c_n, 60000)):
                        名字829 = 区块815.c_off + 读取912 * 32
                        映射852 = 区块815.type_name(句柄256(参数721, 名字829))
                        for 句柄776 in 名字349.finditer(映射852):
                            句柄816.setdefault(句柄776.group(1), set()).add(映射852)
                    for 读取912 in range(min(区块815.s_n, 60000)):
                        节点697 = 区块815.string(读取912)
                        if 节点697.startswith(('https://', 'http://')) and len(节点697) < 200:
                            检查1470 = 节点697.split('//', 1)[-1].split('/')[0].split(':')[0]
                            if '.' in 检查1470 and ' ' not in 检查1470:
                                状态1129.add(检查1470)
                elif name.startswith('res/xml/') and name.endswith('.xml'):
                    try:
                        表744 = 键1023.read(name)
                        if b'pin-set' in 表744 or b'certificate' in 表744:
                            句柄816.setdefault('network-security-config', set()).add(name)
                    except Exception:
                        pass
    except Exception:
        pass
    return (句柄816, sorted(状态1129)[:200])
写入351 = re.compile('(checkServerTrusted|checkClientTrusted|checkTrustedRecursive|checkTrustAnchor|getAcceptedIssuers|setDefaultHostnameVerifier|setSSLSocketFactory|SSLContext;->init|CertificatePinner;->check|CertificateChainCleaner;->clean|verifyHostname|verifyHost|X509TrustManager|setTrustedCertificates|getInstance;->\\"X509\\"|setHostnameVerifier|checkValidity|X509Certificate;->getPublicKey|MessageDigest;->digest)', re.I)

def 读取352(键743, limit=14):
    句柄816 = {}
    try:
        with zipfile.ZipFile(键743) as 键1023:
            for name in sorted((步骤698 for 步骤698 in 键1023.namelist() if re.match('classes\\d*\\.dex$', 步骤698))):
                参数721 = 键1023.read(name)
                for cls, 读取1472, 索引1484 in 文本348(参数721):
                    if not 写入351.search(索引1484 or ''):
                        continue
                    key = (cls, 读取1472)
                    句柄816.setdefault(key, set()).add(索引1484.split('->')[-1].split('(')[0])
    except Exception:
        pass
    打开793 = sorted(句柄816.items(), key=lambda kv: -len(kv[1]))
    return [(cls, 读取1472, sorted(句柄1176)) for (cls, 读取1472), 句柄1176 in 打开793[:limit]]
打开353 = 'com|net|org|io|co|app|dev|me|info|biz|xyz|gov|edu|cloud|site|online|tech|ai|tv|ly|in|dz|sa|ae|fr|uk|de|es|it|ru|cn|tr|ma|tn|eg|qa|kw|be|nl'
关闭354 = re.compile('^[a-z0-9][a-z0-9.\\-]{2,}\\.[a-z0-9.\\-]+\\.[a-z]{2,12}$')
构建355 = re.compile('\\.(?:%s)$' % 打开353)

def 解析356(参数721, want=None, cap=200000, needles=None):
    区块815 = 写入311(参数721)
    if not 区块815.ok:
        return {}
    文本708 = {}
    for 读取912 in range(min(区块815.c_n, 60000)):
        名字829 = 区块815.c_off + 读取912 * 32
        映射852 = 区块815.type_name(句柄256(参数721, 名字829))
        目标1141 = 句柄256(参数721, 名字829 + 24)
        if not 目标1141:
            continue
        值1062 = 目标1141
        try:
            索引1444, 值1062 = 步骤258(参数721, 值1062)
            计数1445, 值1062 = 步骤258(参数721, 值1062)
            路径1446, 值1062 = 步骤258(参数721, 值1062)
            列表1447, 值1062 = 步骤258(参数721, 值1062)
            for 读取1112 in range(索引1444 + 计数1445):
                读取1112, 值1062 = 步骤258(参数721, 值1062)
                读取1112, 值1062 = 步骤258(参数721, 值1062)
            for 列866 in (路径1446, 列表1447):
                结果882 = 0
                for 读取1112 in range(列866):
                    文本1108, 值1062 = 步骤258(参数721, 值1062)
                    结果882 += 文本1108
                    读取1112, 值1062 = 步骤258(参数721, 值1062)
                    栈819, 值1062 = 步骤258(参数721, 值1062)
                    if not 栈819:
                        continue
                    步骤698 = min(句柄256(参数721, 栈819 + 12), cap)
                    键863 = 栈819 + 16
                    for 名字989 in range(步骤698 - 1):
                        目标861 = 区块255(参数721, 键863 + 名字989 * 2)
                        值862 = 目标861 & 255
                        if 值862 not in (26, 27):
                            continue
                        if 值862 == 26:
                            扫描1597 = 区块255(参数721, 键863 + (名字989 + 1) * 2)
                        else:
                            if 名字989 + 2 >= 步骤698:
                                continue
                            扫描1597 = 区块255(参数721, 键863 + (名字989 + 1) * 2) | 区块255(参数721, 键863 + (名字989 + 2) * 2) << 16
                        偏移1414 = 区块815.string(扫描1597)
                        if not 偏移1414 or len(偏移1414) > 90:
                            continue
                        if want is not None and 偏移1414 not in want:
                            continue
                        if needles is not None:
                            if 偏移1414 not in needles:
                                continue
                        elif not (关闭354.match(偏移1414) and 构建355.search(偏移1414)):
                            continue
                        文本708.setdefault(偏移1414, set()).add((映射852, 区块815.method_name(结果882)))
        except Exception:
            continue
    return 文本708
扫描357 = frozenset(('/system/etc/security/cacerts', '/system/etc/security/cacerts/', 'AndroidCAStore', 'cacerts', '/apex/com.android.conscrypt/cacerts'))

def 修补358(键743, limit=10):
    句柄816 = {}
    try:
        with zipfile.ZipFile(键743) as 键1023:
            for name in sorted((步骤698 for 步骤698 in 键1023.namelist() if re.match('classes\\d*\\.dex$', 步骤698))):
                for 条目1533, 写入1471 in 解析356(键1023.read(name), needles=扫描357).items():
                    for cls, 读取1472 in 写入1471:
                        句柄816.setdefault(cls, set()).add(读取1472)
    except Exception:
        return
    if not 句柄816:
        键63.info('no class reads the system CA store directly · the nsc covers the whole process')
        return
    键63.warn('%d class(es) build their own trust store · they ignore network_security_config' % len(句柄816))
    for cls in sorted(句柄816)[:limit]:
        键63.bullet('%s · %s' % (cls.strip('L;').split('/')[-1], ', '.join(sorted(句柄816[cls])[:2])))

def 报告359(键743, limit=12):
    标记1130 = {}
    try:
        with zipfile.ZipFile(键743) as 键1023:
            for name in sorted((步骤698 for 步骤698 in 键1023.namelist() if re.match('classes\\d*\\.dex$', 步骤698))):
                for 检查1470, 写入1471 in 解析356(键1023.read(name)).items():
                    标记1130.setdefault(检查1470, set()).update(写入1471)
    except Exception:
        return
    if not 标记1130:
        键63.info('no host strings found in the dex payload')
        return
    打开793 = sorted(标记1130.items(), key=lambda kv: -len(kv[1]))
    键63.kv('host issuers', len(打开793))
    for 检查1470, 写入1471 in 打开793[:limit]:
        cls = sorted({映射1132.strip('L;').split('/')[-1] for 映射1132, 目标1781 in 写入1471})
        键63.bullet('%s  <- %s' % (检查1470, ', '.join(cls[:3])))

def 变量360(键743):
    打开793 = 读取352(键743)
    if not 打开793:
        键63.info('no method calls the tls/pinning api directly · pinning is not in java code')
        return 打开793
    键63.kv('tls call sites', len(打开793))
    for cls, 读取1472, 句柄1176 in 打开793:
        键63.bullet('%s · %s  <- %s' % (cls.strip('L;').split('/')[-1], 读取1472, ', '.join(句柄1176[:3])))
    return 打开793

def 参数361(状态809, 标记810):
    值702 = ['Java.perform(function () {', '  var targets = [']
    句柄1096 = set()
    for 队列1131 in 状态809.values():
        for 映射852 in 队列1131:
            if not 映射852.startswith('L') or 映射852 in 句柄1096:
                continue
            句柄1096.add(映射852)
            值702.append('    "%s",' % 映射852.replace('/', '.')[1:-1])
    值702 += ['  ];', '  targets.forEach(function (name) {', '    try {', '      var C = Java.use(name);', '      C.checkServerTrusted.overloads.forEach(function (m) { m.implementation = function () { return; }; });', '      C.verify.overloads.forEach(function (m) { m.implementation = function () { return true; }; });', '    } catch (e) {}', '  });', '});']
    return '\n'.join(值702) + '\n'

def 结果362(变量720):
    映射812 = {}
    try:
        for 计数885 in Path(变量720).read_text(encoding='utf-8', errors='ignore').splitlines():
            句柄776 = re.match('^(\\S+) -> (\\S+):$', 计数885.strip())
            if 句柄776:
                映射812[句柄776.group(2).replace('.', '/')] = 句柄776.group(1)
    except Exception:
        pass
    return 映射812

def 缓存363(队列811, 映射812):
    if not 映射812:
        return 队列811
    文本708 = []
    for 映射1132 in 队列811:
        文本708.append(映射812.get(映射1132['name'], 映射1132['name']))
    return 文本708

def 索引364(键743, 条目813):
    步骤978 = []
    try:
        with zipfile.ZipFile(键743) as 键1023:
            for name in 键1023.namelist():
                if not re.match('classes\\d*\\.dex$', name):
                    continue
                参数721 = 键1023.read(name)
                区块815 = 写入311(参数721)
                if not 区块815.ok:
                    continue
                for 映射852, 条目1453 in 条目813:
                    名字829 = 区块815.find_class(映射852)
                    if 名字829 is None:
                        continue
                    目标1141 = 句柄256(参数721, 名字829 + 24)
                    if not 目标1141:
                        continue
                    值1062 = 目标1141
                    索引1444, 值1062 = 步骤258(参数721, 值1062)
                    计数1445, 值1062 = 步骤258(参数721, 值1062)
                    路径1446, 值1062 = 步骤258(参数721, 值1062)
                    列表1447, 值1062 = 步骤258(参数721, 值1062)
                    for 读取1112 in range(索引1444 + 计数1445):
                        读取1112, 值1062 = 步骤258(参数721, 值1062)
                        读取1112, 值1062 = 步骤258(参数721, 值1062)
                    for 列866 in (路径1446, 列表1447):
                        结果882 = 0
                        for 读取1112 in range(列866):
                            文本1108, 值1062 = 步骤258(参数721, 值1062)
                            结果882 += 文本1108
                            读取1112, 值1062 = 步骤258(参数721, 值1062)
                            栈819, 值1062 = 步骤258(参数721, 值1062)
                            if 栈819 and 区块815.method_name(结果882) == 条目1453:
                                列表847 = 参数721[栈819 + 16:栈819 + 16 + 8]
                                if any((节点697 and 列表847.startswith(节点697) for 节点697 in 解析516)):
                                    步骤978.append((name, 映射852, 条目1453))
    except Exception:
        pass
    return 步骤978

def 计数365(name):
    name = name.strip()
    if name.startswith('L') and name.endswith(';'):
        return name
    if '.' in name and '/' not in name:
        name = name.replace('.', '/')
    return 'L' + name + ';'

def 路径366(变量720):
    条目1133 = []
    列表807 = {}
    关闭1114 = []
    try:
        字节747 = Path(变量720).expanduser().read_text(encoding='utf-8', errors='ignore')
    except Exception as 修补958:
        return ([], {}, ['cannot read: ' + str(修补958)[:50]])
    for 打开1473, 计数885 in enumerate(字节747.splitlines(), 1):
        计数885 = 计数885.split('//')[0].strip()
        if not 计数885 or 计数885.startswith('#'):
            continue
        变量760 = 计数885.split()
        if len(变量760) < 2:
            关闭1114.append("line %d · expected 'selector kind'" % 打开1473)
            continue
        值1622, 行705 = (变量760[0], 变量760[1].lower())
        if 行705 not in ('void', 'true', 'false'):
            关闭1114.append('line %d · kind must be void, true or false' % 打开1473)
            continue
        if '#' in 值1622:
            cls, 读取1472 = 值1622.split('#', 1)
            if not cls or not 读取1472:
                关闭1114.append('line %d · empty class or method' % 打开1473)
                continue
            条目1133.append((计数365(cls), 读取1472, 行705))
        else:
            列表807[值1622] = 行705
    return (条目1133, 列表807, 关闭1114)

def 列表367(键743, 计数725, limit=200):
    路径1046 = re.compile(计数725, re.I)
    步骤978 = []
    try:
        with zipfile.ZipFile(键743) as 键1023:
            for name in 键1023.namelist():
                if not re.match('classes\\d*\\.dex$', name):
                    continue
                参数721 = 键1023.read(name)
                区块815 = 写入311(参数721)
                if not 区块815.ok:
                    continue
                句柄1096 = set()
                for 读取912 in range(min(区块815.m_n, 400000)):
                    try:
                        值1782 = 区块815.method_name(读取912)
                    except Exception:
                        continue
                    if not 路径1046.search(值1782):
                        continue
                    try:
                        映射852 = 区块815.type_name(区块255(参数721, 区块815.m_off + 读取912 * 8))
                    except Exception:
                        continue
                    key = (映射852, 值1782)
                    if key in 句柄1096:
                        continue
                    句柄1096.add(key)
                    步骤978.append((name, 映射852, 值1782))
                    if len(步骤978) >= limit:
                        return 步骤978
    except Exception:
        pass
    return 步骤978

def 数据368(args):
    缓存3.probe()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    变量720, 键1383 = 条目573(args.input)
    if not 变量720.exists():
        键63.bad('missing ' + str(变量720))
        return 2
    键63.head('method index', 字节27)
    键63.kv('pattern', args.methods)
    步骤978 = 列表367(变量720, args.methods)
    if not 步骤978:
        键63.info('no method matched')
        return 0
    键63.ok('%d method(s)' % len(步骤978))
    for 值1422, 映射852, 读取1472 in 步骤978:
        关闭1474 = 映射852.replace('/', '.')[1:-1] if 映射852.startswith('L') else 映射852
        print('  ' + 报告39(映射52) + ' ' + 修补38(关闭1474 + '#' + 读取1472) + 打开33('  · ' + 值1422))
    print()
    键63.info('paste any line above into a targets file, then run with --targets')
    return 0

def 状态369(args):
    缓存3.probe()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    字节787 = Path(args.batch).expanduser()
    if 字节787.is_file():
        区块895 = [字节787]
    elif 字节787.is_dir():
        区块895 = sorted((值1062 for 值1062 in 字节787.rglob('*') if 值1062.suffix.lower() in ('.apk', '.apks', '.xapk', '.apkm')))
    else:
        键63.bad('batch path not found')
        return 2
    if not 区块895:
        键63.bad('no archives under ' + str(字节787))
        return 2
    键63.head('batch', 行25)
    键63.kv('archives', len(区块895))
    偏移1134 = []
    for 区块815, 区块1415 in enumerate(区块895, 1):
        print()
        print('  ' + 栈59('[%d/%d] %s' % (区块815, len(区块895), 区块1415.name), 行25, True))
        args.input = str(区块1415)
        args.output = None
        try:
            code = 路径246(args)
        except Exception as 修补958:
            键63.bad('crashed · ' + 节点57(str(修补958), 90))
            code = 1
        偏移1134.append((区块1415.name, code))
    键63.head('batch summary', 文本28)
    区块1135 = sum((1 for 读取1112, 映射1132 in 偏移1134 if 映射1132 == 0))
    键63.kv('succeeded', 区块1135)
    键63.kv('failed', len(偏移1134) - 区块1135)
    for name, code in 偏移1134:
        区块1095 = 关闭34(数据48) if code == 0 else 解析36(状态49)
        print('  ' + 区块1095 + ' ' + 修补38(节点57(name, 60)) + 打开33('  code %d' % code))
    return 0 if 区块1135 == len(偏移1134) else 6
句柄136 = ('checkSignature', 'verifySignature', 'validateSignature', 'isSignatureValid', 'isSignatureCorrect', 'verifyAppSignature', 'checkAppSignature', 'isSignedCorrectly', 'checkSignatures', 'verifyIntegrity', 'checkIntegrity', 'validateAppSignature', 'isSignatureVerified', 'verifySignatures')
节点137 = ('isTampered', 'checkTampered', 'isAppTampered', 'isSignatureInvalid', 'isModified')
标记370 = {'AdMob': ['com/google/android/gms/ads'], 'Facebook Audience': ['com/facebook/ads'], 'Unity Ads': ['com/unity3d/ads'], 'AppLovin': ['com/applovin'], 'IronSource': ['com/ironsource'], 'Vungle': ['com/vungle'], 'Chartboost': ['com/chartboost'], 'MoPub': ['com/mopub'], 'Pangle': ['com/bytedance/sdk/openadsdk', 'com/pangle'], 'Mintegral': ['com/mintegral'], 'InMobi': ['com/inmobi'], 'StartApp': ['com/startapp'], 'AdColony': ['com/adcolony'], 'Tapjoy': ['com/tapjoy'], 'Smaato': ['com/smaato'], 'Yandex Ads': ['com/yandex/mobile/ads'], 'Amazon Ads': ['com/amazon/device/ads'], 'Appodeal': ['com/appodeal'], 'Fyber': ['com/fyber'], 'AdMost': ['com/admost']}
队列371 = ['com/android/billingclient', 'com/android/vending/billing', 'IInAppBillingService', 'com/google/android/play/billing', 'BillingClient']
映射372 = ['com/google/android/vending/licensing', 'LicenseChecker', 'LicenseValidator', 'com.android.vending.CHECK_LICENSE', 'ILicensingService']
条目373 = ['GET_SIGNATURES', 'GET_SIGNING_CERTIFICATES', 'getPackageInfo']

def 偏移374(参数721, 偏移814):
    区块815 = 写入311(参数721)
    if not 区块815.ok:
        return (bytearray(参数721), [])
    计数805 = bytearray(参数721)
    步骤978 = []
    limit = min(区块815.c_n, 60000)
    for 读取912 in range(limit):
        名字829 = 区块815.c_off + 读取912 * 32
        映射852 = 区块815.type_name(句柄256(计数805, 名字829))
        目标1141 = 句柄256(计数805, 名字829 + 24)
        if not 目标1141:
            continue
        值1062 = 目标1141
        try:
            索引1444, 值1062 = 步骤258(计数805, 值1062)
            计数1445, 值1062 = 步骤258(计数805, 值1062)
            路径1446, 值1062 = 步骤258(计数805, 值1062)
            列表1447, 值1062 = 步骤258(计数805, 值1062)
            for 读取1112 in range(索引1444 + 计数1445):
                读取1112, 值1062 = 步骤258(计数805, 值1062)
                读取1112, 值1062 = 步骤258(计数805, 值1062)
            for 列866 in (路径1446, 列表1447):
                结果882 = 0
                for 读取1112 in range(列866):
                    文本1108, 值1062 = 步骤258(计数805, 值1062)
                    结果882 += 文本1108
                    读取1112, 值1062 = 步骤258(计数805, 值1062)
                    栈819, 值1062 = 步骤258(计数805, 值1062)
                    if not 栈819:
                        continue
                    name = 区块815.method_name(结果882)
                    行705 = 偏移814.get(name)
                    if not 行705:
                        continue
                    行705 = 区块815.stub_kind(结果882, 行705)
                    标记1010 = 缓存323(计数805, 栈819)
                    计数1005 = bytes(计数805[栈819:标记1010]) if 标记1010 else None
                    if not 标记330(计数805, 栈819, 行705):
                        continue
                    if 标记1010 is None or 缓存323(计数805, 栈819) != 标记1010 or (not 队列331(计数805, 栈819, 行705)):
                        if 计数1005:
                            计数805[栈819:标记1010] = 计数1005
                        参数321['failures'].append((映射852, name, 栈819))
                        continue
                    步骤978.append((映射852, name, 栈819, 行705))
        except Exception:
            continue
    if 步骤978:
        打开313(计数805)
    return (计数805, 步骤978)

def 区块375(区块815, cap=100000):
    文本708 = []
    for 读取912 in range(min(getattr(区块815, '报告1399', 0), cap)):
        文本708.append(区块815.type_name(读取912))
    return 文本708

def 句柄376(键743):
    句柄816 = {'ads': {}, 'iap': [], 'license': [], 'sig': [], 'classes': 0}
    try:
        with zipfile.ZipFile(键743) as 键1023:
            for name in 键1023.namelist():
                if not re.match('classes\\d*\\.dex$', name):
                    continue
                区块815 = 写入311(键1023.read(name))
                if not 区块815.ok:
                    continue
                数据728 = 区块375(区块815, 250000)
                句柄816['classes'] += len(数据728)
                for 映射852 in 数据728:
                    关闭1074 = 映射852.lower()
                    for 修补718, 计数845 in 标记370.items():
                        if any((打开1793 in 关闭1074 for 打开1793 in 计数845)):
                            句柄816['ads'].setdefault(修补718, 映射852)
                            break
                    for 变量1760 in 队列371:
                        if 变量1760.lower() in 关闭1074 and 变量1760 not in 句柄816['iap']:
                            句柄816['iap'].append(变量1760)
                    for 变量1760 in 映射372:
                        if 变量1760.lower() in 关闭1074 and 变量1760 not in 句柄816['license']:
                            句柄816['license'].append(变量1760)
                    for 变量1760 in 条目373:
                        if 变量1760.lower() in 关闭1074 and 变量1760 not in 句柄816['sig']:
                            句柄816['sig'].append(变量1760)
    except Exception:
        pass
    return 句柄816

def 节点377(句柄816):
    键63.head('monetisation map', 字节27)
    句柄1136 = 句柄816.get('ads', {})
    if 句柄1136:
        键63.kv('ad networks', len(句柄1136), width=22)
        for 修补718 in sorted(句柄1136):
            键63.bullet('%s · %s' % (修补718, 节点57(句柄1136[修补718], 60)))
    else:
        键63.info('no known ad sdk found')
    键63.kv('in-app billing', 'present' if 句柄816.get('iap') else 'absent', width=22, 写入791=构建35 if 句柄816.get('iap') else 打开33)
    for 句柄776 in 句柄816.get('iap', [])[:4]:
        键63.bullet(句柄776)
    键63.kv('license check', 'present' if 句柄816.get('license') else 'absent', width=22, 写入791=构建35 if 句柄816.get('license') else 打开33)
    for 句柄776 in 句柄816.get('license', [])[:4]:
        键63.bullet(句柄776)
    键63.kv('signature checks', 'present' if 句柄816.get('sig') else 'absent', width=22, 写入791=构建35 if 句柄816.get('sig') else 打开33)
    for 句柄776 in 句柄816.get('sig', [])[:4]:
        键63.bullet(句柄776)

def 步骤378(变量720, limit=400):
    try:
        import capstone
    except ImportError:
        return (None, 'capstone not installed · pip install capstone')
    数据848 = 行265(变量720)
    if not 数据848.ok:
        return (None, 'not an elf object')
    节点1137 = {'aarch64': (capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM), 'arm': (capstone.CS_ARCH_ARM, capstone.CS_MODE_THUMB), 'x86_64': (capstone.CS_ARCH_X86, capstone.CS_MODE_64), 'x86': (capstone.CS_ARCH_X86, capstone.CS_MODE_32)}
    步骤1138 = 节点1137.get(数据848.machine)
    if not 步骤1138:
        return (None, 'unsupported isa ' + 数据848.machine)
    text = next((节点697 for 节点697 in 数据848.sections if 节点697['name'] == '.text'), None)
    if not text:
        return (None, 'no .text section')
    try:
        with open(变量720, 'rb') as 构建915:
            构建915.seek(text['offset'])
            表744 = 构建915.read(min(text['size'], 64 * 1024))
        构建1475 = capstone.Cs(步骤1138[0], 步骤1138[1])
        构建1475.detail = True
        文本708 = []
        for 值1142 in 构建1475.disasm(表744, text['offset']):
            文本708.append('0x%06x  %-8s %s' % (值1142.address, 值1142.mnemonic, 值1142.op_str))
            if len(文本708) >= limit:
                break
        return (文本708, None)
    except Exception as 修补958:
        return (None, 节点57(str(修补958), 60))
栈379 = 'https://github.com/skylot/jadx/releases/download/v1.5.1/jadx-1.5.1.zip'

def 源380(写入751):
    字节787 = HOME / 'jadx'
    if (字节787 / 'lib').is_dir() and any((字节787 / 'lib').glob('jadx-*.jar')):
        return 字节787
    if not 文本108():
        return None
    dest = Path(写入751) / 'jadx.zip'
    if not 栈179(栈379, dest, 'jadx'):
        return None
    try:
        字节787.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest) as 键1023:
            键1023.extractall(字节787)
        for 值1062 in 字节787.rglob('*'):
            if 值1062.is_file() and 值1062.suffix in ('.sh', ''):
                try:
                    os.chmod(值1062, 493)
                except Exception:
                    pass
        return 字节787 if (字节787 / 'lib').is_dir() else None
    except Exception:
        return None

def 目标381(写入751, 键743, 节点817):
    字节787 = 源380(写入751)
    if not 字节787:
        return (False, 'jadx unavailable')
    栈1139 = str(字节787 / 'lib' / '*')
    节点817 = Path(节点817)
    节点817.mkdir(parents=True, exist_ok=True)
    字节707, 读取1112 = 关闭114(['java'] + 键183() + ['-cp', 栈1139, 'jadx.cli.JadxCLI', '-d', str(节点817), '--no-res', str(键743)], 'jadx decompile', timeout=3600)
    if 字节707 == 0 and any(节点817.rglob('*.java')):
        return (True, str(节点817))
    return (False, 'jadx produced no sources')

def 值382():
    条目693 = [1] * 256
    for 值862, 步骤698 in ((2, 2), (3, 3), (5, 2), (6, 3), (8, 2), (9, 3), (19, 2), (20, 3), (21, 2), (22, 2), (23, 3), (24, 5), (25, 2), (26, 2), (27, 3), (28, 2), (31, 2), (32, 2), (34, 2), (35, 2), (36, 3), (37, 3), (38, 3), (41, 2), (42, 3), (43, 3), (44, 3), (250, 4), (251, 4), (252, 3), (253, 3), (254, 2), (255, 2)):
        条目693[值862] = 步骤698
    for 值862 in range(45, 62):
        条目693[值862] = 2
    for 值862 in range(82, 110):
        条目693[值862] = 2
    for 值862 in range(110, 115):
        条目693[值862] = 3
    for 值862 in range(116, 121):
        条目693[值862] = 3
    for 值862 in range(208, 227):
        条目693[值862] = 2
    return 条目693
键383 = 值382()
表384 = set(range(110, 115)) | set(range(116, 121))
行385 = set(range(50, 62))
列386 = {26, 27}
字节387 = {28, 31, 32, 34, 35, 36, 37}
文本388 = set(range(82, 95)) | set(range(96, 110))

def 名字389(步骤818):
    return 步骤818 - 256 if 步骤818 & 128 else 步骤818

def 检查390(步骤818):
    return 步骤818 - 65536 if 步骤818 & 32768 else 步骤818

def 写入391(步骤818):
    return 步骤818 - 4294967296 if 步骤818 & 2147483648 else 步骤818

class 读取392:

    def __init__(self, 行705, 表864, 结果922):
        self.kind = 行705
        self.pc = 表864
        self.detail = 结果922

    def as_dict(self):
        return {'kind': self.kind, 'pc': self.pc, 'detail': self.detail}

def 打开393(参数721, 栈819, 源820=200000):
    缓存923 = []
    索引924 = []
    if 栈819 <= 0 or 栈819 + 16 > len(参数721):
        索引924.append(读取392('code-offset-out-of-range', -1, 'code_off=0x%x' % 栈819))
        return (缓存923, 索引924)
    字节867 = 句柄256(参数721, 栈819 + 12)
    键863 = 栈819 + 16
    if 字节867 == 0:
        return (缓存923, 索引924)
    if 键863 + 字节867 * 2 > len(参数721):
        索引924.append(读取392('insns-exceed-file', 0, 'declared %d units, file ends early' % 字节867))
        字节867 = max(0, (len(参数721) - 键863) // 2)
    表864 = 0
    while 表864 < 字节867:
        if len(缓存923) >= 源820:
            索引924.append(读取392('decode-budget', 表864, 'stopped after %d instructions' % 源820))
            break
        目标861 = 区块255(参数721, 键863 + 表864 * 2)
        值862 = 目标861 & 255
        关闭914 = 键383[值862]
        if 关闭914 <= 0 or 表864 + 关闭914 > 字节867:
            索引924.append(读取392('instruction-truncated', 表864, 'op=0x%02x needs %d units' % (值862, 关闭914)))
            break
        区块1415 = {'pc': 表864, 'op': 值862, 'size': 关闭914, 'target': None, 'ref': None, 'kind': None, 'reg': None, 'lit': None}
        if 值862 == 18:
            区块1415['reg'] = 目标861 >> 8 & 15
            区块1415['lit'] = 目标861 >> 12 & 15
        elif 值862 in (19, 20, 21, 22, 23, 24, 25):
            区块1415['reg'] = 目标861 >> 8 & 255
        try:
            if 值862 in (40,):
                区块1415['target'] = 表864 + 名字389(目标861 >> 8)
                区块1415['kind'] = 'goto'
            elif 值862 == 41:
                区块1415['target'] = 表864 + 检查390(区块255(参数721, 键863 + (表864 + 1) * 2))
                区块1415['kind'] = 'goto'
            elif 值862 == 42:
                字节747 = 区块255(参数721, 键863 + (表864 + 1) * 2) << 16 | 区块255(参数721, 键863 + (表864 + 2) * 2)
                区块1415['target'] = 表864 + 写入391(字节747)
                区块1415['kind'] = 'goto'
            elif 值862 in 行385:
                区块1415['target'] = 表864 + 检查390(区块255(参数721, 键863 + (表864 + 1) * 2))
                区块1415['kind'] = 'branch'
            elif 值862 in (43, 44):
                字节747 = 区块255(参数721, 键863 + (表864 + 1) * 2) << 16 | 区块255(参数721, 键863 + (表864 + 2) * 2)
                区块1415['target'] = 表864 + 写入391(字节747)
                区块1415['kind'] = 'switch'
            elif 值862 in 表384 or 值862 in (250, 251, 252, 253):
                区块1415['ref'] = 区块255(参数721, 键863 + (表864 + 1) * 2)
                区块1415['kind'] = 'invoke'
            elif 值862 in 列386:
                if 值862 == 26:
                    区块1415['ref'] = 区块255(参数721, 键863 + (表864 + 1) * 2)
                else:
                    区块1415['ref'] = 句柄256(参数721, 键863 + (表864 + 1) * 2)
                区块1415['kind'] = 'string'
            elif 值862 in 字节387:
                区块1415['ref'] = 区块255(参数721, 键863 + (表864 + 1) * 2)
                区块1415['kind'] = 'type'
            elif 值862 in 文本388:
                区块1415['ref'] = 区块255(参数721, 键863 + (表864 + 1) * 2)
                区块1415['kind'] = 'field'
            if 区块1415['target'] is not None and (not 0 <= 区块1415['target'] < 字节867):
                索引924.append(读取392('branch-out-of-bounds', 表864, 'target %d outside 0..%d' % (区块1415['target'], 字节867 - 1)))
                区块1415['target'] = None
        except Exception as 修补958:
            索引924.append(读取392('operand-read-failed', 表864, 节点57(str(修补958), 60)))
            break
        缓存923.append(区块1415)
        表864 += 关闭914
    return (缓存923, 索引924)

class 关闭394:

    def __init__(self, 目标821, 队列891, name, 栈819, 缓存923, 索引924, 计数925, 路径926):
        self.dex = 目标821
        self.descriptor = 队列891
        self.name = name
        self.code_off = 栈819
        self.insns = 缓存923
        self.issues = 索引924
        self.registers = 计数925
        self.params = 路径926

    def evidence(self):
        return {'dex': self.dex, 'class': self.descriptor, 'method': self.name, 'code_off': '0x%x' % self.code_off, 'instructions': len(self.insns)}

def 构建395(目标821, 参数721, 值822=20000, 键823=200000):
    区块815 = 写入311(参数721)
    if not 区块815.ok:
        return
    源1140 = 0
    for 读取912 in range(min(区块815.c_n, 60000)):
        名字829 = 区块815.c_off + 读取912 * 32
        映射852 = 区块815.type_name(句柄256(参数721, 名字829))
        目标1141 = 句柄256(参数721, 名字829 + 24)
        if not 目标1141:
            continue
        值1062 = 目标1141
        try:
            索引1444, 值1062 = 步骤258(参数721, 值1062)
            计数1445, 值1062 = 步骤258(参数721, 值1062)
            路径1446, 值1062 = 步骤258(参数721, 值1062)
            列表1447, 值1062 = 步骤258(参数721, 值1062)
            for 读取1112 in range(索引1444 + 计数1445):
                读取1112, 值1062 = 步骤258(参数721, 值1062)
                读取1112, 值1062 = 步骤258(参数721, 值1062)
            for 列866 in (路径1446, 列表1447):
                结果882 = 0
                for 读取1112 in range(列866):
                    文本1108, 值1062 = 步骤258(参数721, 值1062)
                    结果882 += 文本1108
                    读取1112, 值1062 = 步骤258(参数721, 值1062)
                    栈819, 值1062 = 步骤258(参数721, 值1062)
                    if not 栈819:
                        continue
                    缓存923, 索引924 = 打开393(参数721, 栈819, 值822)
                    yield 关闭394(目标821, 映射852, 区块815.method_name(结果882), 栈819, 缓存923, 索引924, 区块255(参数721, 栈819), 区块255(参数721, 栈819 + 2))
                    源1140 += 1
                    if 源1140 >= 键823:
                        return
        except Exception:
            continue

def 解析396(区块815, 表824):
    try:
        键863 = 区块815.m_off + 表824 * 8
        cls = 区块815.type_name(区块255(区块815.d, 键863))
        name = 区块815.string(句柄256(区块815.d, 键863 + 4))
        return '%s->%s' % (cls, name)
    except Exception:
        return '?'

class 扫描397:

    def __init__(self, 键743):
        self.apk = 键743
        self.methods = 0
        self.instructions = 0
        self.issues = []
        self.calls = {}
        self.callers = {}
        self.strings = {}
        self.classes = set()
        self.budget_hit = False

    def as_dict(self):
        return {'methods_decoded': self.methods, 'instructions': self.instructions, 'integrity_issues': len(self.issues), 'distinct_call_edges': len(self.calls), 'classes': len(self.classes), 'budget_truncated': self.budget_hit}

def 修补398(键743, 行825=60000, 列826=6000000):
    字节827 = 扫描397(键743)
    try:
        with zipfile.ZipFile(键743) as 键1023:
            for name in 键1023.namelist():
                if not re.match('classes\\d*\\.dex$', name):
                    continue
                参数721 = 键1023.read(name)
                区块815 = 写入311(参数721)
                if not 区块815.ok:
                    字节827.issues.append({'dex': name, 'kind': 'header-invalid', 'pc': -1, 'detail': 'not a dex'})
                    continue
                for 节点1497 in 构建395(name, 参数721, 20000, 行825):
                    字节827.methods += 1
                    字节827.instructions += len(节点1497.insns)
                    字节827.classes.add(节点1497.descriptor)
                    for 解析1476 in 节点1497.issues:
                        字节827.issues.append(dict(解析1476.as_dict(), dex=name, class_=节点1497.descriptor, method=节点1497.name))
                    if 字节827.instructions > 列826:
                        字节827.budget_hit = True
                        return 字节827
                    for 值1142 in 节点1497.insns:
                        if 值1142['kind'] == 'invoke' and 值1142['ref'] is not None:
                            索引1484 = 解析396(区块815, 值1142['ref'])
                            节点1177 = '%s->%s' % (节点1497.descriptor, 节点1497.name)
                            字节827.calls.setdefault(节点1177, set()).add(索引1484)
                            字节827.callers.setdefault(索引1484, set()).add(节点1177)
                        elif 值1142['kind'] == 'string' and 值1142['ref'] is not None:
                            偏移1414 = 区块815.string(值1142['ref'])
                            字节827.strings.setdefault(偏移1414, []).append(节点1497.evidence())
    except Exception as 修补958:
        字节827.issues.append({'dex': '-', 'kind': 'archive-error', 'pc': -1, 'detail': 节点57(str(修补958), 80)})
    return 字节827

def 报告399(字节827):
    键63.head('dex integrity', 字节27)
    键63.kv('methods decoded', 字节827.methods)
    键63.kv('instructions', 字节827.instructions)
    键63.kv('classes', len(字节827.classes))
    键63.kv('call edges', sum((len(步骤818) for 步骤818 in 字节827.calls.values())))
    键63.kv('string refs', len(字节827.strings))
    if 字节827.budget_hit:
        键63.warn('scan budget reached · results are partial')
    if 字节827.issues:
        报告1279 = {}
        for 解析1476 in 字节827.issues:
            报告1279[解析1476.get('kind')] = 报告1279.get(解析1476.get('kind'), 0) + 1
        读取1432 = {名字989: 步骤818 for 名字989, 步骤818 in 报告1279.items() if 名字989 not in ('instruction-truncated', 'decode-budget')}
        if 读取1432:
            键63.warn('%d decode problem(s)' % sum(读取1432.values()))
            for 行705, 列866 in sorted(读取1432.items(), key=lambda kv: -kv[1]):
                键63.bullet('%s · %d' % (行705, 列866))
        标记1450 = sum((步骤818 for 名字989, 步骤818 in 报告1279.items() if 名字989 in ('instruction-truncated', 'decode-budget')))
        if 标记1450:
            键63.info('%d method(s) ended mid instruction · common in obfuscated or packed code' % 标记1450)
        if not 读取1432 and (not 标记1450):
            键63.warn('%d integrity issue(s)' % len(字节827.issues))
    else:
        键63.ok('every decoded instruction stayed inside its method bounds')
变量400 = {'Ljavax/net/ssl/X509TrustManager;': ('x509-trust-manager', 'critical'), 'Ljavax/net/ssl/TrustManager;': ('trust-manager', 'high'), 'Ljavax/net/ssl/HostnameVerifier;': ('hostname-verifier', 'high'), 'Lokhttp3/CertificatePinner;': ('okhttp-pinner', 'critical'), 'Lcom/squareup/okhttp/CertificatePinner;': ('okhttp3-pinner', 'critical')}
参数401 = ('checkServerTrusted', 'checkClientTrusted', 'verify', 'getAcceptedIssuers', 'check')

def 结果402(参数721, 文本828):
    行745 = 句柄256(参数721, 文本828 + 12)
    if not 行745 or 行745 + 4 > len(参数721):
        return []
    关闭914 = 句柄256(参数721, 行745)
    文本708 = []
    for 读取912 in range(min(关闭914, 256)):
        变量1280 = 行745 + 4 + 读取912 * 2
        if 变量1280 + 2 > len(参数721):
            break
        文本708.append(区块255(参数721, 变量1280))
    return 文本708

def 缓存403(参数721, 区块815, 名字829):
    目标1141 = 句柄256(参数721, 名字829 + 24)
    if not 目标1141:
        return
    值1062 = 目标1141
    索引1444, 值1062 = 步骤258(参数721, 值1062)
    计数1445, 值1062 = 步骤258(参数721, 值1062)
    路径1446, 值1062 = 步骤258(参数721, 值1062)
    列表1447, 值1062 = 步骤258(参数721, 值1062)
    for 读取1112 in range(索引1444 + 计数1445):
        读取1112, 值1062 = 步骤258(参数721, 值1062)
        读取1112, 值1062 = 步骤258(参数721, 值1062)
    for 列866 in (路径1446, 列表1447):
        结果882 = 0
        for 读取1112 in range(列866):
            文本1108, 值1062 = 步骤258(参数721, 值1062)
            结果882 += 文本1108
            读取1112, 值1062 = 步骤258(参数721, 值1062)
            栈819, 值1062 = 步骤258(参数721, 值1062)
            yield (区块815.method_name(结果882), 栈819)

def 索引404(参数721, 区块815, 栈819, limit=4000):
    缓存923, 索引924 = 打开393(参数721, 栈819, limit)
    文本708 = []
    for 值1142 in 缓存923:
        if 值1142['kind'] == 'string' and 值1142['ref'] is not None:
            偏移1414 = 区块815.string(值1142['ref'])
            if 偏移1414 and 偏移1414 not in 文本708:
                文本708.append(偏移1414)
    return (文本708, 缓存923, 索引924)

def 计数405(键743):
    检查830 = []
    写入831 = {'present': False, 'entry': None, 'pins': [], 'anchors': [], 'cleartext': None}
    try:
        with zipfile.ZipFile(键743) as 键1023:
            数据728 = 键1023.namelist()
            for name in 数据728:
                if not re.match('classes\\d*\\.dex$', name):
                    continue
                参数721 = 键1023.read(name)
                区块815 = 写入311(参数721)
                if not 区块815.ok:
                    continue
                for 读取912 in range(min(区块815.c_n, 60000)):
                    名字829 = 区块815.c_off + 读取912 * 32
                    映射852 = 区块815.type_name(句柄256(参数721, 名字829))
                    构建1635 = [区块815.type_name(条目693) for 条目693 in 结果402(参数721, 名字829)]
                    参数1761 = 句柄256(参数721, 名字829 + 8)
                    修补1598 = 区块815.type_name(参数1761) if 参数1761 != 4294967295 else ''
                    for 扫描1637, (行705, 状态1449) in 变量400.items():
                        if 扫描1637 not in 构建1635 and 扫描1637 != 修补1598:
                            continue
                        写入1631 = list(缓存403(参数721, 区块815, 名字829))
                        参数1481 = [(句柄776, 行745) for 句柄776, 行745 in 写入1631 if 句柄776 in 参数401 and 行745]
                        if not 参数1481:
                            continue
                        for 读取1712, 行745 in 参数1481:
                            值982, 缓存923, 索引924 = 索引404(参数721, 区块815, 行745)
                            扫描1197 = [节点697 for 节点697 in 值982 if '://' in 节点697 or ('.' in 节点697 and len(节点697) < 120 and (' ' not in 节点697))]
                            检查830.append({'kind': 行705, 'severity': 状态1449, 'confidence': 1.0 if 扫描1637 in 构建1635 else 0.75, 'dex': name, 'class': 映射852, 'method': 读取1712, 'code_off': '0x%x' % 行745, 'interfaces': 构建1635, 'super': 修补1598, 'strings': 扫描1197[:12], 'instructions': len(缓存923), 'issues': [报告1079.kind for 报告1079 in 索引924]})
                        break
                continue
            for name in 数据728:
                if not (name.startswith('res/xml/') and name.endswith('.xml')):
                    continue
                表744 = 键1023.read(name)
                if b'pin-set' not in 表744 and b'trust-anchors' not in 表744 and (b'network-security-config' not in 表744):
                    continue
                写入831['present'] = True
                写入831['entry'] = name
                表904 = 报告279(表744)
                修补1638 = []
                句柄1296 = []
                for 队列1411, 映射1412, 节点1417, 偏移1414 in 表904.attrs:
                    if 映射1412 == 'pin' and 节点1417 == 'digest':
                        修补1638.append(偏移1414)
                    if 映射1412 == 'certificates' and 节点1417 == 'src':
                        句柄1296.append(偏移1414)
                    if 映射1412 == 'base-config' and 节点1417 == 'cleartextTrafficPermitted':
                        写入831['cleartext'] = 偏移1414
                写入831['pins'] = 修补1638
                写入831['anchors'] = 句柄1296
                检查830.append({'kind': 'network-security-config', 'severity': 'high' if 修补1638 else 'medium', 'confidence': 1.0, 'dex': None, 'class': name, 'method': None, 'code_off': None, 'interfaces': [], 'super': '', 'strings': 修补1638[:8] + 句柄1296[:8], 'instructions': 0, 'issues': []})
                break
    except Exception as 修补958:
        检查830.append({'kind': 'analysis-error', 'severity': 'info', 'confidence': 0.0, 'dex': None, 'class': '-', 'method': None, 'code_off': None, 'interfaces': [], 'super': '', 'strings': [], 'instructions': 0, 'issues': [节点57(str(修补958), 80)]})
    return (检查830, 写入831)

def 路径406(检查830, 写入831):
    键63.head('certificate validation paths', 字节27)
    if not 检查830:
        键63.info('no trust manager, pinner or pin set found')
        return
    for 读取952 in 检查830:
        写入791 = 索引4(打开233(读取952['severity']), 读取952['severity'] in ('critical', 'high'))
        扫描1477 = 读取952['dex'] or '-'
        print('  ' + 写入791(映射52) + ' ' + 写入791(读取952['kind'].upper().ljust(22)) + 修补38(节点57(读取952['class'], 54)))
        键63.kv('evidence', '%s · %s · %s' % (扫描1477, 读取952['method'] or '-', 读取952['code_off'] or '-'), width=22)
        键63.kv('confidence', '%.2f' % 读取952['confidence'], width=22)
        if 读取952['super']:
            键63.kv('extends', 读取952['super'], width=22)
        if 读取952['interfaces']:
            键63.kv('implements', ', '.join((报告1079.replace('/', '.').strip('L;') for 报告1079 in 读取952['interfaces'][:4])), width=22)
        for 节点697 in 读取952['strings'][:5]:
            print('    ' + 打开33(路径46 + ' ' + 节点57(节点697, 88)))
        if 读取952['issues']:
            键63.warn('%d decoder issue(s) in this method' % len(读取952['issues']))
    if 写入831['present']:
        键63.kv('pin set', '%d pin(s) · %d anchor(s)' % (len(写入831['pins']), len(写入831['anchors'])), width=22)
列表407 = {'x509-trust-manager': ('Install the build on a test device, add a user CA, route HTTPS through a proxy.', 'the handshake must be rejected; readable traffic means validation is bypassable'), 'trust-manager': ('Repeat the user-CA proxy test against every endpoint the app calls.', 'all pinned hosts must reject the proxy certificate'), 'hostname-verifier': ('Connect to the backend through a proxy with a certificate issued for a different hostname.', 'the connection must fail; success means hostname checks are ineffective'), 'okhttp-pinner': ('Proxy the app and inspect the first request to each pinned host.', 'each pinned host must abort the handshake'), 'okhttp3-pinner': ('Proxy the app and inspect the first request to each pinned host.', 'each pinned host must abort the handshake'), 'network-security-config': ('Check whether the config trusts user certificates and whether cleartext is allowed.', 'user anchors must be absent in release builds')}

def 数据408(检查830):
    构建835 = []
    for 读取952 in 检查830:
        修补1478 = 列表407.get(读取952['kind'])
        if not 修补1478:
            continue
        键1623, 表1624 = 修补1478
        构建835.append({'id': 'CERT-%s-%s' % (读取952['kind'], 读取952['method'] or 'config'), 'category': 'certificate-validation', 'target': {'dex': 读取952['dex'], 'class': 读取952['class'], 'method': 读取952['method'], 'code_off': 读取952['code_off']}, 'confidence': 读取952['confidence'], 'scenario': 键1623, 'expected': 表1624, 'evidence': 读取952['strings'][:5]})
    return 构建835
状态409 = ('class', 'method', 'string', 'symbol', 'path')
标记410 = ('critical', 'high', 'medium', 'low', 'info')

def 队列411(变量720):
    状态729 = Path(变量720).expanduser()
    if not 状态729.exists():
        return (None, 'rules file not found')
    try:
        text = 状态729.read_text(encoding='utf-8', errors='ignore')
    except Exception as 修补958:
        return (None, 'cannot read rules: ' + 节点57(str(修补958), 60))
    参数721 = None
    if 状态729.suffix.lower() in ('.yaml', '.yml'):
        try:
            import yaml
        except ImportError:
            return (None, 'PyYAML is not installed · pip install pyyaml, or use a .json rules file')
        try:
            参数721 = yaml.safe_load(text)
        except Exception as 修补958:
            return (None, 'yaml parse error: ' + 节点57(str(修补958), 60))
    else:
        try:
            参数721 = json.loads(text)
        except Exception as 修补958:
            return (None, 'json parse error: ' + 节点57(str(修补958), 60))
    键1143 = 参数721.get('rules') if isinstance(参数721, dict) else 参数721
    if not isinstance(键1143, list):
        return (None, "rules file must contain a list under 'rules'")
    打开833 = []
    关闭1114 = []
    for 读取912, 区块1415 in enumerate(键1143):
        if not isinstance(区块1415, dict):
            关闭1114.append('rule %d is not an object' % 读取912)
            continue
        数据1288 = 区块1415.get('match') or {}
        if not isinstance(数据1288, dict):
            关闭1114.append('rule %d match is not an object' % 读取912)
            continue
        报告1479 = {}
        for 变量1480 in 状态409:
            计数725 = 数据1288.get(变量1480)
            if not 计数725:
                continue
            try:
                报告1479[变量1480] = re.compile(str(计数725), re.I)
            except re.error as 修补958:
                关闭1114.append('rule %d field %s: bad regex (%s)' % (读取912, 变量1480, 修补958))
        if not 报告1479:
            关闭1114.append('rule %d has no usable match field' % 读取912)
            continue
        区块775 = str(区块1415.get('severity', 'medium')).lower()
        if 区块775 not in 标记410:
            区块775 = 'medium'
        try:
            步骤1138 = float(区块1415.get('confidence', 0.5))
        except Exception:
            步骤1138 = 0.5
        打开833.append({'id': str(区块1415.get('id') or 'rule-%d' % 读取912), 'title': str(区块1415.get('title') or 区块1415.get('id') or 'rule-%d' % 读取912), 'severity': 区块775, 'confidence': max(0.0, min(1.0, 步骤1138)), 'tags': [str(条目693) for 条目693 in 区块1415.get('tags') or []], 'match': 报告1479, 'note': str(区块1415.get('note') or '')})
    return (打开833, 关闭1114)

def 映射412(键743, 读取832=120000):
    关闭834 = {'class': set(), 'method': set(), 'string': set(), 'symbol': set(), 'path': set()}
    try:
        with zipfile.ZipFile(键743) as 键1023:
            for name in 键1023.namelist():
                关闭834['path'].add(name)
            for name in 键1023.namelist():
                if re.match('classes\\d*\\.dex$', name):
                    参数721 = 键1023.read(name)
                    区块815 = 写入311(参数721)
                    if not 区块815.ok:
                        continue
                    for 读取912 in range(min(区块815.t_n, 200000)):
                        关闭834['class'].add(区块815.type_name(读取912))
                    for 读取912 in range(min(区块815.m_n, 200000)):
                        关闭834['method'].add(区块815.method_name(读取912))
                    for 读取912 in range(min(区块815.s_n, 读取832)):
                        关闭834['string'].add(区块815.string(读取912))
                elif name.startswith('lib/') and name.endswith('.so'):
                    扫描797 = Path(tempfile.mkdtemp()) / 列106(name)
                    try:
                        with 键1023.open(name) as 状态729, open(扫描797, 'wb') as 索引764:
                            shutil.copyfileobj(状态729, 索引764)
                        数据848 = 行265(扫描797)
                        if 数据848.ok:
                            for 节点697 in 数据848.imports:
                                关闭834['symbol'].add(节点697)
                            for 节点697 in getattr(数据848, 'symtab_names', []):
                                关闭834['symbol'].add(节点697)
                    finally:
                        shutil.rmtree(扫描797.parent, ignore_errors=True)
    except Exception:
        pass
    return 关闭834

def 条目413(打开833, 关闭834):
    检查830 = []
    for 目标61 in 打开833:
        参数1481 = {}
        ok = True
        for 变量1480, 路径1046 in 目标61['match'].items():
            步骤978 = [报告1079 for 报告1079 in 关闭834.get(变量1480, ()) if 路径1046.search(报告1079)]
            if not 步骤978:
                ok = False
                break
            参数1481[变量1480] = sorted(步骤978)[:10]
        if not ok:
            continue
        结果1482 = 目标61['confidence']
        if 结果1482 == 0.5 and len(参数1481) > 1:
            结果1482 = min(0.95, 0.5 + 0.15 * len(参数1481))
        检查830.append({'id': 目标61['id'], 'title': 目标61['title'], 'severity': 目标61['severity'], 'confidence': round(结果1482, 2), 'tags': 目标61['tags'], 'note': 目标61['note'], 'evidence': 参数1481, 'source': 'custom-rule'})
    return 检查830

def 偏移414(检查830):
    键63.head('custom rule findings', 字节27)
    if not 检查830:
        键63.info('no custom rule matched')
        return
    for 读取952 in 检查830:
        写入791 = 索引4(打开233(读取952['severity']), 读取952['severity'] in ('critical', 'high'))
        print('  ' + 写入791(映射52) + ' ' + 写入791(读取952['severity'].upper().ljust(9)) + 修补38(读取952['title']) + 打开33('  ·  confidence %.2f' % 读取952['confidence']))
        for 变量1480, 步骤978 in 读取952['evidence'].items():
            for 解析956 in 步骤978[:3]:
                print('    ' + 打开33('%s: %s' % (变量1480, 节点57(解析956, 84))))

def 区块415(键703, 关闭794, 检查830, 构建835, 列表727):
    打开793 = []
    for 读取952 in 检查830:
        缓存1483 = '<br>'.join((解析276('%s: %s' % (名字989, 步骤818)) for 名字989, 修补1678 in 读取952.get('evidence', {}).items() for 步骤818 in 修补1678[:2]))
        打开793.append("<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td><td class='ev'>%s</td></tr>" % (解析276(读取952.get('severity', '')), 解析276(读取952.get('title', 读取952.get('kind', ''))), 解析276('%.2f' % 读取952.get('confidence', 0)), 解析276(读取952.get('source', 'builtin')), 缓存1483 or '-'))
    表1144 = ''.join(('<tr><td>%s</td><td>%s</td><td>%s</td><td>%s</td></tr>' % (解析276(映射1132['id']), 解析276(映射1132['scenario']), 解析276(映射1132['expected']), 解析276(str(映射1132['target']))) for 映射1132 in 构建835))
    修补1078 = 'body{margin:0;background:#080b12;color:#e2e8f0;font:14px/1.6 ui-monospace,Menlo,monospace;padding:36px 18px}.w{max-width:1100px;margin:auto}h1{font-size:24px;background:linear-gradient(90deg,#67e8f9,#818cf8,#e879f9);-webkit-background-clip:text;background-clip:text;color:transparent}h2{font-size:14px;letter-spacing:1.3px;color:#22d3ee;text-transform:uppercase;margin-top:28px}table{width:100%;border-collapse:collapse;font-size:12.5px}th{background:#0b1220;color:#94a3b8;text-align:left;padding:7px 9px}td{padding:6px 9px;border-top:1px solid #1e293b;vertical-align:top}.ev{color:#94a3b8;word-break:break-all}section{border:1px solid #1e293b;border-radius:14px;background:#101725;padding:18px 20px;margin-top:16px}footer{color:#64748b;text-align:center;margin-top:24px;font-size:12px}'
    return "<!DOCTYPE html><html lang='en'><head><meta charset='utf-8'><title>%s</title><style>%s</style></head><body><div class='w'><h1>%s</h1><p style='color:#94a3b8'>%s · %s</p><section><h2>Findings</h2><table><tr><th>Severity</th><th>Title</th><th>Confidence</th><th>Source</th><th>Evidence</th></tr>%s</table></section><section><h2>Defensive test cases</h2><table><tr><th>ID</th><th>Scenario</th><th>Expected</th><th>Target</th></tr>%s</table></section><section><h2>Scan statistics</h2><table>%s</table></section><footer>%s %s</footer></div></body></html>" % (解析276(键703), 修补1078, 解析276(键703), 解析276(str(关闭794)), 解析276(time.strftime('%Y-%m-%d %H:%M')), ''.join(打开793) or "<tr><td colspan='5'>none</td></tr>", 表1144 or "<tr><td colspan='4'>none</td></tr>", ''.join(('<tr><th>%s</th><td>%s</td></tr>' % (解析276(名字989), 解析276(str(步骤818))) for 名字989, 步骤818 in 列表727.items())), 写入71, 读取72)

def 句柄416(解析836, 扫描837, 修补838, 报告839):
    文本708 = []
    for 读取952 in 解析836:
        文本708.append({'severity': 读取952['severity'], 'title': 读取952['kind'], 'confidence': 读取952['confidence'], 'source': 'builtin', 'evidence': {'dex': [str(读取952['dex'])], 'class': [读取952['class']], 'method': [str(读取952['method'])], 'offset': [str(读取952['code_off'])], 'strings': 读取952['strings'][:5]}})
    if 扫描837.get('ads'):
        文本708.append({'severity': 'low', 'title': 'ad-networks', 'confidence': 1.0, 'source': 'builtin', 'evidence': {'sdk': sorted(扫描837['ads'])}})
    if 扫描837.get('iap'):
        文本708.append({'severity': 'medium', 'title': 'in-app-billing', 'confidence': 1.0, 'source': 'builtin', 'evidence': {'marker': 扫描837['iap'][:5]}})
    if 扫描837.get('license'):
        文本708.append({'severity': 'high', 'title': 'license-check', 'confidence': 1.0, 'source': 'builtin', 'evidence': {'marker': 扫描837['license'][:5]}})
    if 扫描837.get('sig'):
        文本708.append({'severity': 'medium', 'title': 'signature-checks', 'confidence': 0.9, 'source': 'builtin', 'evidence': {'marker': 扫描837['sig'][:5]}})
    for 读取952 in 修补838:
        文本708.append(读取952)
    for 修补958 in 报告839:
        解析956 = 修补958.summary().get('hardening', {})
        状态1209 = [名字989 for 名字989, 步骤818 in 解析956.items() if not 步骤818]
        if 状态1209:
            文本708.append({'severity': 'low', 'title': 'native-hardening-gap', 'confidence': 0.8, 'source': 'builtin', 'evidence': {'object': [修补958.name], 'missing': 状态1209}})
    return 文本708

def 节点417(args):
    计数5.reset()
    缓存3.probe()
    关闭714 = args.no_anim or not 缓存3.enabled
    if not args.quiet:
        节点97(关闭714)
        print()
    状态729, 键1383 = 条目573(args.input)
    if not 状态729.exists():
        键63.bad('input not found: ' + str(状态729))
        return 2
    if not 检查310(状态729):
        return 8
    打开833 = []
    if args.rules:
        打开833, 关闭1114 = 队列411(args.rules)
        if 打开833 is None:
            键63.bad(关闭1114)
            return 3
        if 关闭1114:
            for 值1062 in 关闭1114:
                键63.warn(值1062)
        键63.head('rules', 列26)
        键63.kv('loaded', '%d rule(s)' % len(打开833))
    键63.head('1 · detection', 行25)
    区块815 = 列266(状态729)
    键63.kv('entries', 区块815['total'])
    键63.kv('dex files', len(区块815['dex']))
    键63.kv('native', len(区块815['so']))
    索引884 = None
    try:
        with zipfile.ZipFile(状态729) as 键1023:
            索引884 = 区块615(键1023)[1]
    except Exception:
        索引884 = None
    if 索引884:
        键63.kv('package', 索引884['package'])
        键63.kv('version', '%s (%s)' % (索引884['version'], 索引884.get('version_code', '?')))
    键63.head('2 · evidence', 字节27)
    解析836, 写入831 = 计数405(状态729)
    路径406(解析836, 写入831)
    键63.head('3 · method mapping', 字节27)
    行1145 = 修补398(状态729)
    报告399(行1145)
    键63.head('4 · cross references', 字节27)
    列1146 = sorted(行1145.callers.items(), key=lambda kv: -len(kv[1]))[:8]
    if not 列1146:
        键63.info('no call edges collected')
    for 索引1484, 句柄856 in 列1146:
        键63.kv(节点57(索引1484, 56), '%d caller(s)' % len(句柄856), width=58)
    键63.head('5 · native analysis', 字节27)
    报告839 = 打开273(状态729, None)
    if not 报告839:
        键63.info('no native objects')
    for 修补958 in 报告839[:12]:
        节点697 = 修补958.summary()
        解析956 = 节点697['hardening']
        表1024 = ''.join(['P' if 解析956.get('pie') else '-', 'N' if 解析956.get('nx') else '-', 'R' if 解析956.get('relro') else '-', 'C' if 解析956.get('canary') else '-'])
        键63.kv(修补958.name, '%s · %s · %s' % (节点697['machine'], 表1024, 表104(节点697['size'])), width=34)
    键63.head('6 · custom rules', 字节27)
    修补838 = []
    if 打开833:
        关闭834 = 映射412(状态729)
        键63.kv('facts', 'class %d · method %d · string %d · symbol %d · path %d' % (len(关闭834['class']), len(关闭834['method']), len(关闭834['string']), len(关闭834['symbol']), len(关闭834['path'])), width=12)
        修补838 = 条目413(打开833, 关闭834)
        偏移414(修补838)
    else:
        键63.info('no rules file supplied · pass --rules to add your own')
    扫描837 = 句柄376(状态729)
    字节1147 = 句柄416(解析836, 扫描837, 修补838, 报告839)
    构建835 = 数据408(解析836)
    键63.head('7 · test cases', 文本28)
    if not 构建835:
        键63.info('no defensive test case generated')
    for 映射1132 in 构建835:
        print('  ' + 报告39(映射52) + ' ' + 修补38(映射1132['id']))
        print('    ' + 打开33('scenario  ' + 节点57(映射1132['scenario'], 92)))
        print('    ' + 打开33('expected  ' + 节点57(映射1132['expected'], 92)))
    文本1148 = None
    if args.baseline:
        键863 = Path(args.baseline).expanduser()
        if not 键863.exists():
            键63.warn('baseline not found · ' + str(键863))
        else:
            键63.head('8 · regression', 文本28)
            检查1710, 读取1112 = 计数405(键863)
            行1625 = 句柄376(键863)
            列1626 = 条目413(打开833, 映射412(键863)) if 打开833 else []
            字节1627 = 句柄416(检查1710, 行1625, 列1626, [])
            key = lambda 读取952: (读取952['title'], tuple(读取952.get('evidence', {}).get('class', [])))
            标记1010 = {key(读取952) for 读取952 in 字节1627}
            结果1202 = {key(读取952) for 读取952 in 字节1147}
            文本1428 = 标记1010 - 结果1202
            文本1628 = 标记1010 & 结果1202
            字节987 = 结果1202 - 标记1010
            键63.kv('resolved', len(文本1428), width=18)
            键63.kv('still present', len(文本1628), width=18)
            键63.kv('newly introduced', len(字节987), width=18)
            for 条目693, 读取1112 in sorted(文本1428)[:10]:
                print('    ' + 关闭34(数据48) + ' ' + 打开33(条目693))
            for 条目693, 读取1112 in sorted(文本1628)[:10]:
                print('    ' + 构建35(队列51) + ' ' + 打开33(条目693))
            文本1148 = {'resolved': [条目693 for 条目693, 读取1112 in 文本1428], 'remaining': [条目693 for 条目693, 读取1112 in 文本1628], 'added': [条目693 for 条目693, 读取1112 in 字节987]}
    条目1053 = Path(args.output).expanduser() if args.output else HOME / ('%s_security' % 状态729.stem)
    条目1053.mkdir(parents=True, exist_ok=True)
    名字1149 = 行1145.as_dict()
    名字1149.update({'archive_entries': 区块815['total'], 'dex_files': len(区块815['dex']), 'native_objects': len(报告839), 'findings': len(字节1147), 'test_cases': len(构建835), 'rules_loaded': len(打开833)})
    检查1150 = 区块415('Android security test report', 状态729, 字节1147, 构建835, 名字1149)
    行105(条目1053 / 'report.html', 检查1150, 'w')
    行105(条目1053 / 'findings.json', json.dumps({'target': str(状态729), 'stats': 名字1149, 'findings': 字节1147, 'regression': 文本1148}, indent=2, default=str), 'w')
    行105(条目1053 / 'testcases.json', json.dumps(构建835, indent=2, default=str), 'w')
    行105(条目1053 / 'integrity.json', json.dumps(行1145.issues, indent=2, default=str), 'w')
    缓存283()
    键63.head('9 · verification report', 文本28)
    写入1151 = sum((1 for 读取952 in 字节1147 if 读取952['severity'] == 'critical'))
    读取1152 = sum((1 for 读取952 in 字节1147 if 读取952['severity'] == 'high'))
    键63.kv('findings', '%d critical · %d high · %d total' % (写入1151, 读取1152, len(字节1147)))
    键63.kv('dex integrity', 'clean' if not 行1145.issues else '%d issue(s)' % len(行1145.issues))
    索引284('report', [str(条目1053 / 'report.html'), 'findings  %d' % len(字节1147), 'cases     %d' % len(构建835), 'integrity %s' % ('clean' if not 行1145.issues else 'issues')], 文本28)
    return 0
步骤418 = ('stub-method', 'replace-string', 'manifest-attr')
栈419 = ('void', 'true', 'false')

def 源420(标记730):
    return len(节点257(max(0, 标记730)))

def 目标421(参数721, 映射812, limit=20000):
    区块815 = 写入311(参数721)
    if not 区块815.ok:
        return (bytearray(参数721), [], [])
    计数805 = bytearray(参数721)
    步骤978 = []
    打开1153 = []
    句柄1096 = set()
    for 读取912 in range(min(区块815.s_n, 400000)):
        if len(步骤978) >= limit:
            break
        行745 = 句柄256(计数805, 区块815.s_off + 读取912 * 4)
        if 行745 <= 0 or 行745 >= len(计数805):
            continue
        try:
            写入1711, 值1062 = 步骤258(计数805, 行745)
            名字1629 = 计数805[值1062:值1062 + 写入1711]
            源900 = 名字1629.decode('utf-8', 'replace')
        except Exception:
            continue
        if 源900 not in 映射812 or 源900 in 句柄1096:
            continue
        目标901 = 映射812[源900]
        if 目标901 == 源900:
            continue
        计数1485 = 目标901.encode('utf-8')
        路径1486 = len(目标901.encode('utf-16-le')) // 2
        if 源420(路径1486) != 源420(写入1711) or len(计数1485) > len(名字1629):
            打开1153.append({'string': 节点57(源900, 60), 'reason': 'does not fit in place'})
            continue
        句柄1416 = 节点257(路径1486)
        计数805[行745:行745 + len(句柄1416)] = 句柄1416
        start = 行745 + len(句柄1416)
        计数805[start:start + len(计数1485)] = 计数1485
        for 名字989 in range(start + len(计数1485), 值1062 + len(名字1629)):
            计数805[名字989] = 0
        句柄1096.add(源900)
        步骤978.append({'from': 节点57(源900, 60), 'to': 节点57(目标901, 60), 'offset': '0x%x' % 行745})
    if 步骤978:
        打开313(计数805)
    return (计数805, 步骤978, 打开1153)

def 值422(变量720):
    状态729 = Path(变量720).expanduser()
    if not 状态729.exists():
        return (None, 'patch file not found')
    try:
        参数721 = json.loads(状态729.read_text(encoding='utf-8', errors='ignore'))
    except Exception as 修补958:
        return (None, 'json parse error: ' + 节点57(str(修补958), 70))
    if isinstance(参数721, list):
        参数721 = {'patches': 参数721}
    if not isinstance(参数721, dict) or not isinstance(参数721.get('patches'), list):
        return (None, "patch file must contain a 'patches' list")
    关闭1114 = []
    关闭1154 = []
    for 读取912, 区块1415 in enumerate(参数721['patches']):
        if not isinstance(区块1415, dict):
            关闭1114.append('patch %d is not an object' % 读取912)
            continue
        action = str(区块1415.get('action', '')).lower()
        节点1217 = str(区块1415.get('id') or 'patch-%d' % 读取912)
        if action not in 步骤418:
            关闭1114.append("%s · unknown action '%s'" % (节点1217, action))
            continue
        读取872 = {'id': 节点1217, 'title': str(区块1415.get('title') or 节点1217), 'action': action, 'conflicts': [str(映射1132) for 映射1132 in 区块1415.get('conflicts') or []], 'note': str(区块1415.get('note') or '')}
        if action == 'stub-method':
            路径806 = 区块1415.get('targets') or []
            if not isinstance(路径806, list) or not 路径806:
                关闭1114.append('%s · stub-method needs a targets list' % 节点1217)
                continue
            行705 = str(区块1415.get('kind', 'true')).lower()
            if 行705 not in 栈419:
                关闭1114.append('%s · kind must be void, true or false' % 节点1217)
                continue
            读取872['targets'] = [str(条目693) for 条目693 in 路径806]
            读取872['kind'] = 行705
        elif action == 'replace-string':
            if 'from' not in 区块1415 or 'to' not in 区块1415:
                关闭1114.append('%s · replace-string needs from and to' % 节点1217)
                continue
            读取872['from'] = str(区块1415['from'])
            读取872['to'] = str(区块1415['to'])
        elif action == 'manifest-attr':
            if 'attr' not in 区块1415:
                关闭1114.append('%s · manifest-attr needs attr' % 节点1217)
                continue
            读取872['attr'] = str(区块1415['attr'])
            读取872['value'] = 区块1415.get('value', True)
        关闭1154.append(读取872)
    构建1155 = 参数721.get('profiles') or {}
    if not isinstance(构建1155, dict):
        关闭1114.append('profiles must be an object')
        构建1155 = {}
    return ({'name': str(参数721.get('name') or 'unnamed'), 'schema': str(参数721.get('schema') or 'arp-patch/1'), 'patches': 关闭1154, 'profiles': 构建1155}, 关闭1114)

def 键423(变量840, 参数841):
    解析1156 = {值1062['id']: 值1062 for 值1062 in 变量840['patches']}
    if 参数841:
        扫描1157 = 变量840['profiles'].get(参数841)
        if 扫描1157 is None:
            return (None, "profile '%s' is not defined" % 参数841)
        结果842 = [解析1156[读取912] for 读取912 in 扫描1157 if 读取912 in 解析1156]
        状态1209 = [读取912 for 读取912 in 扫描1157 if 读取912 not in 解析1156]
        if 状态1209:
            return (None, 'profile references unknown patches: ' + ', '.join(状态1209))
        return (结果842, None)
    return (list(变量840['patches']), None)

def 表424(结果842):
    扫描1157 = {值1062['id'] for 值1062 in 结果842}
    修补1158 = []
    for 值1062 in 结果842:
        for 列表1487 in 值1062['conflicts']:
            if 列表1487 in 扫描1157:
                字节1547 = tuple(sorted((值1062['id'], 列表1487)))
                if 字节1547 not in 修补1158:
                    修补1158.append(字节1547)
    return 修补1158

def 行425(结果842, 键743):
    report = []
    try:
        with zipfile.ZipFile(键743) as 键1023:
            缓存1523 = {步骤698: 键1023.read(步骤698) for 步骤698 in 键1023.namelist() if re.match('classes\\d*\\.dex$', 步骤698)}
            检查1630 = 'AndroidManifest.xml' in 键1023.namelist()
    except Exception as 修补958:
        return [{'id': '-', 'ok': False, 'detail': 'archive unreadable: ' + 节点57(str(修补958), 50)}]
    报告1159 = {步骤698: 写入311(映射692) for 步骤698, 映射692 in 缓存1523.items()}
    for 值1062 in 结果842:
        if 值1062['action'] == 'stub-method':
            句柄816 = []
            for 条目693 in 值1062['targets']:
                if '#' in 条目693:
                    cls, 读取1472 = 条目693.split('#', 1)
                    映射852 = 计数365(cls)
                    写入1551 = any((区块815.find_class(映射852) is not None for 区块815 in 报告1159.values() if 区块815.ok))
                    句柄816.append((条目693, 写入1551))
                else:
                    写入1551 = False
                    for 区块815 in 报告1159.values():
                        if not 区块815.ok:
                            continue
                        for 读取912 in range(min(区块815.m_n, 200000)):
                            if 区块815.method_name(读取912) == 条目693:
                                写入1551 = True
                                break
                        if 写入1551:
                            break
                    句柄816.append((条目693, 写入1551))
            状态1209 = [条目693 for 条目693, ok in 句柄816 if not ok]
            report.append({'id': 值1062['id'], 'ok': not 状态1209, 'detail': 'all targets resolved' if not 状态1209 else 'missing: ' + ', '.join(状态1209[:4])})
        elif 值1062['action'] == 'replace-string':
            列866 = 0
            for 区块815 in 报告1159.values():
                if not 区块815.ok:
                    continue
                for 读取912 in range(min(区块815.s_n, 200000)):
                    if 区块815.string(读取912) == 值1062['from']:
                        列866 += 1
                        break
            report.append({'id': 值1062['id'], 'ok': 列866 > 0, 'detail': 'string present' if 列866 else 'string not found in any dex'})
        elif 值1062['action'] == 'manifest-attr':
            report.append({'id': 值1062['id'], 'ok': 检查1630, 'detail': 'manifest present' if 检查1630 else 'no AndroidManifest.xml'})
    return report

def 列426(键743, 文本708, 结果842, 缓存843=None):
    变量1160 = {'tool': 写入71, 'version': 读取72, 'input': str(键743), 'output': str(文本708), 'backup': None, 'applied': [], 'skipped': [], 'timestamp': time.strftime('%Y-%m-%d %H:%M:%S')}
    参数1161 = []
    列表807 = {}
    结果1162 = {}
    缓存1163 = []
    for 值1062 in 结果842:
        if 值1062['action'] == 'stub-method':
            for 条目693 in 值1062['targets']:
                if '#' in 条目693:
                    cls, 读取1472 = 条目693.split('#', 1)
                    参数1161.append((计数365(cls), 读取1472, 值1062['kind']))
                else:
                    列表807[条目693] = 值1062['kind']
        elif 值1062['action'] == 'replace-string':
            结果1162[值1062['from']] = 值1062['to']
        elif 值1062['action'] == 'manifest-attr':
            偏移1414 = 值1062['value']
            if isinstance(偏移1414, bool):
                缓存1163.append((值1062['attr'], 18, 4294967295 if 偏移1414 else 0))
            elif isinstance(偏移1414, int):
                缓存1163.append((值1062['attr'], 16, 偏移1414))
            else:
                缓存1163.append((值1062['attr'], 3, str(偏移1414)))
    if 缓存843:
        数据1488 = Path(缓存843)
        数据1488.mkdir(parents=True, exist_ok=True)
        状态1489 = 数据1488 / (Path(键743).name + '.orig')
        shutil.copy2(键743, 状态1489)
        变量1160['backup'] = str(状态1489)
    索引1164 = None
    try:
        with zipfile.ZipFile(键743) as 名字1429, zipfile.ZipFile(文本708, 'w') as 检查1430:
            for 区块1415 in 名字1429.infolist():
                name = 区块1415.filename
                if name.upper().startswith('META-INF/') and name.upper().endswith(('.SF', '.RSA', '.DSA', '.EC', '.MF')):
                    continue
                参数761 = 名字1429.read(name)
                if re.match('classes\\d*\\.dex$', name):
                    计数805 = bytearray(参数761)
                    if 参数1161:
                        计数805, 步骤978 = 映射332(bytes(计数805), 参数1161)
                        if 步骤978:
                            变量1160['applied'].append({'id': 'stub-method', 'dex': name, 'changes': ['%s#%s' % (解析956[0], 解析956[1]) for 解析956 in 步骤978]})
                    if 列表807:
                        栈1779, 源1780 = 偏移374(bytes(计数805), 列表807)
                        if 源1780:
                            计数805 = 栈1779
                            变量1160['applied'].append({'id': 'stub-method', 'dex': name, 'changes': ['%s#%s' % (解析956[0], 解析956[1]) for 解析956 in 源1780]})
                    if 结果1162:
                        名字1789, 检查1790, 写入1791 = 目标421(bytes(计数805), 结果1162)
                        if 检查1790:
                            计数805 = 名字1789
                            变量1160['applied'].append({'id': 'replace-string', 'dex': name, 'changes': 检查1790})
                        for 节点697 in 写入1791:
                            变量1160['skipped'].append(dict(节点697, dex=name))
                    参数761 = bytes(计数805)
                elif name == 'AndroidManifest.xml':
                    索引1164 = 参数761
                状态1609 = zipfile.ZipInfo(name, date_time=区块1415.date_time)
                状态1609.compress_type = 区块1415.compress_type
                状态1609.external_attr = 区块1415.external_attr
                状态1609.internal_attr = 区块1415.internal_attr
                状态1609.create_system = 区块1415.create_system
                检查1430.writestr(状态1609, 参数761)
    except Exception as 修补958:
        if Path(文本708).exists():
            Path(文本708).unlink(missing_ok=True)
        return (None, 'apply failed: ' + 节点57(str(修补958), 70))
    if 缓存1163 and 索引1164 is not None:
        源1620, 栈979 = 栈339(索引1164, 缓存1163)
        if 源1620:
            扫描797 = Path(str(文本708) + '.m')
            try:
                with zipfile.ZipFile(文本708) as 名字1429, zipfile.ZipFile(扫描797, 'w') as 检查1430:
                    for 区块1415 in 名字1429.infolist():
                        参数761 = 源1620 if 区块1415.filename == 'AndroidManifest.xml' else 名字1429.read(区块1415.filename)
                        状态1609 = zipfile.ZipInfo(区块1415.filename, date_time=区块1415.date_time)
                        状态1609.compress_type = 区块1415.compress_type
                        状态1609.external_attr = 区块1415.external_attr
                        状态1609.internal_attr = 区块1415.internal_attr
                        状态1609.create_system = 区块1415.create_system
                        检查1430.writestr(状态1609, 参数761)
                os.replace(扫描797, 文本708)
                变量1160['applied'].append({'id': 'manifest-attr', 'changes': 栈979})
            except Exception as 修补958:
                扫描797.unlink(missing_ok=True)
                变量1160['skipped'].append({'string': 'manifest', 'reason': 节点57(str(修补958), 50)})
    return (变量1160, None)

def 字节427(索引844, 关闭794=None):
    try:
        变量1160 = json.loads(Path(索引844).expanduser().read_text(encoding='utf-8'))
    except Exception as 修补958:
        return (False, 'journal unreadable: ' + 节点57(str(修补958), 60))
    计数1165 = 变量1160.get('backup')
    dest = 关闭794 or 变量1160.get('output')
    if not 计数1165 or not Path(计数1165).exists():
        return (False, 'backup missing')
    if not dest:
        return (False, 'no destination recorded')
    try:
        shutil.copy2(计数1165, dest)
        return (True, dest)
    except Exception as 修补958:
        return (False, 节点57(str(修补958), 60))

def 文本428(args):
    缓存3.probe()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    if args.revert:
        ok, 结果922 = 字节427(args.revert, args.output)
        键63.head('revert', 文本28 if ok else 检查30)
        if ok:
            键63.ok('restored ' + 结果922)
            return 0
        键63.bad(结果922)
        return 3
    if not args.patch or not args.input:
        键63.bad('--patch needs --input')
        return 2
    键743, 键1383 = 条目573(args.input)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    变量840, 关闭1114 = 值422(args.patch)
    if 变量840 is None:
        键63.bad(关闭1114)
        return 3
    for 值1062 in 关闭1114:
        键63.warn(值1062)
    结果842, 名字709 = 键423(变量840, args.profile)
    if 结果842 is None:
        键63.bad(名字709)
        return 3
    键63.head('patch set', 行25)
    键63.kv('file', 变量840['name'])
    键63.kv('patches', len(变量840['patches']))
    键63.kv('selected', len(结果842))
    if args.profile:
        键63.kv('profile', args.profile)
    修补1158 = 表424(结果842)
    if 修补1158:
        键63.warn('%d conflict pair(s)' % len(修补1158))
        for 队列691, 映射692 in 修补1158:
            键63.bullet('%s <-> %s' % (队列691, 映射692))
        if not args.force:
            键63.bad('resolve the conflicts or pass --force')
            return 4
    report = 行425(结果842, 键743)
    键63.head('validation', 列26)
    bad = 0
    for 名字909 in report:
        if 名字909['ok']:
            键63.ok('%s · %s' % (名字909['id'], 名字909['detail']))
        else:
            bad += 1
            键63.bad('%s · %s' % (名字909['id'], 名字909['detail']))
    if bad and (not args.force):
        键63.bad('validation failed · pass --force to apply anyway')
        return 5
    文本708 = Path(args.output).expanduser() if args.output else 映射572(键743, 'patched')
    变量1160, 名字709 = 列426(键743, 文本708, 结果842, 缓存843=str(文本708) + '.backup')
    if 变量1160 is None:
        键63.bad(名字709)
        return 6
    索引844 = Path(str(文本708) + '.journal.json')
    行105(索引844, json.dumps(变量1160, indent=2), 'w')
    键63.head('applied', 文本28)
    total = 0
    for 读取872 in 变量1160['applied']:
        步骤698 = len(读取872['changes'])
        total += 步骤698
        键63.ok('%s · %s · %d change(s)' % (读取872['id'], 读取872.get('dex', 'manifest'), 步骤698))
    for 节点697 in 变量1160['skipped']:
        键63.warn('skipped · %s · %s' % (节点697.get('string'), 节点697.get('reason')))
    if total == 0:
        键63.warn('no change was applied')
    文本708, 检查1390 = 缓存203({}, 文本708, 文本708.parent)
    键63.kv('output', str(文本708))
    键63.kv('journal', str(索引844))
    键63.kv('backup', 变量1160.get('backup') or '-')
    键63.info('revert with: --revert ' + str(索引844))
    return 0
名字429 = ('init', 'start', 'setup', 'prepare', 'configure', 'bootstrap', 'load')
检查430 = ('show', 'present', 'display', 'render', 'interstitial', 'rewarded', 'banner')
写入431 = ('getPackageInfo', 'GET_SIGNATURES', 'GET_SIGNING_CERTIFICATES', 'getInstallerPackageName', 'PackageManager', 'signatures', 'Signature', 'certificate', 'MessageDigest')
读取432 = ('com/google/android/vending/licensing', 'LicenseChecker', 'LicenseValidator', 'ILicensingService')
打开433 = ('com/android/billingclient', 'BillingClient', 'com/android/vending/billing', 'IInAppBillingService')

def 关闭434(键743):
    try:
        with zipfile.ZipFile(键743) as 键1023:
            for name in 键1023.namelist():
                if re.match('classes\\d*\\.dex$', name):
                    yield (name, 键1023.read(name))
    except Exception:
        return

def 构建435(键743, 计数845, 修补718, 路径846=400):
    句柄816 = {}
    for 值1422, 参数721 in 关闭434(键743):
        区块815 = 写入311(参数721)
        if not 区块815.ok:
            continue
        for 读取912 in range(min(区块815.c_n, 60000)):
            名字829 = 区块815.c_off + 读取912 * 32
            映射852 = 区块815.type_name(句柄256(参数721, 名字829))
            关闭1074 = 映射852.lower()
            if not any((值1062.lower() in 关闭1074 for 值1062 in 计数845)):
                continue
            读取872 = 句柄816.setdefault(映射852, {'dex': 值1422, 'class': 映射852, 'methods': [], 'init': [], 'show': []})
            for 读取1712, 栈819 in 缓存403(参数721, 区块815, 名字829):
                if len(读取872['methods']) < 60:
                    读取872['methods'].append(读取1712)
                打开1713 = 读取1712.lower()
                if any((解析956 in 打开1713 for 解析956 in 名字429)) and len(读取872['init']) < 12:
                    读取872['init'].append(读取1712)
                if any((解析956 in 打开1713 for 解析956 in 检查430)) and len(读取872['show']) < 12:
                    读取872['show'].append(读取1712)
            if len(句柄816) >= 路径846:
                break
    return 句柄816

def 解析436(键743):
    文本708 = []
    列表1167 = ('sign', 'certif', 'tamper', 'integrity', 'installer', 'packageinfo')
    for 值1422, 参数721 in 关闭434(键743):
        区块815 = 写入311(参数721)
        if not 区块815.ok:
            continue
        for 读取912 in range(min(区块815.c_n, 60000)):
            名字829 = 区块815.c_off + 读取912 * 32
            映射852 = 区块815.type_name(句柄256(参数721, 名字829))
            写入1631 = [句柄776 for 句柄776, 行745 in 缓存403(参数721, 区块815, 名字829) if 行745]
            if not 写入1631:
                continue
            步骤978 = [句柄776 for 句柄776 in 写入1631 if 句柄776 in 句柄136 or 句柄776 in 节点137]
            if not 步骤978:
                步骤978 = [句柄776 for 句柄776 in 写入1631 if any((名字989 in 句柄776.lower() for 名字989 in 列表1167))]
            if not 步骤978:
                continue
            读取1632 = any((名字989 in 映射852.lower() for 名字989 in ('signature', 'integrity', 'tamper', 'sig')))
            文本708.append({'dex': 值1422, 'class': 映射852, 'methods': 步骤978[:8], 'confidence': 0.9 if 读取1632 and any((句柄776 in 句柄136 or 句柄776 in 节点137 for 句柄776 in 步骤978)) else 0.7})
    return 文本708
扫描437 = {'1': '_', '2': ';', '3': '[', '0': '/'}

def 修补438(列表847):
    缓存963 = []
    数据1168 = ''
    读取912 = 0
    while 读取912 < len(列表847):
        映射1132 = 列表847[读取912]
        if 映射1132 == '_' and 读取912 + 1 < len(列表847) and 列表847[读取912 + 1].isdigit():
            数据1168 += 扫描437.get(列表847[读取912 + 1], 列表847[读取912 + 1])
            读取912 += 2
            continue
        if 映射1132 == '_':
            缓存963.append(数据1168)
            数据1168 = ''
            读取912 += 1
            continue
        数据1168 += 映射1132
        读取912 += 1
    缓存963.append(数据1168)
    return 缓存963

def 报告439(数据848):
    映射812 = []
    for 状态1169 in getattr(数据848, 'symtab_names', []):
        if not 状态1169.startswith('Java_'):
            continue
        缓存963 = 修补438(状态1169[len('Java_'):])
        if len(缓存963) < 2:
            continue
        映射812.append({'symbol': 状态1169, 'class': '/'.join(缓存963[:-1]), 'method': 缓存963[-1]})
    return 映射812

def 变量440(变量720):
    数据848 = 行265(变量720)
    if not 数据848.ok:
        return (None, 'not an elf object')
    标记1170 = []
    try:
        with open(变量720, 'rb') as 构建915:
            for 目标1221 in 数据848.sections:
                if 目标1221['type'] not in (4, 9):
                    continue
                扫描917 = 24 if 数据848.bits == 64 and 目标1221['type'] == 4 else 16 if 数据848.bits == 64 else 12 if 目标1221['type'] == 4 else 8
                列866 = min(目标1221['size'] // 扫描917 if 扫描917 else 0, 50000)
                构建915.seek(目标1221['offset'])
                表744 = 构建915.read(扫描917 * 列866)
                for 读取912 in range(列866):
                    键863 = 读取912 * 扫描917
                    if 键863 + 扫描917 > len(表744):
                        break
                    if 数据848.bits == 64:
                        键1783 = struct.unpack_from('<Q', 表744, 键863)[0]
                        表1784 = struct.unpack_from('<Q', 表744, 键863 + 8)[0]
                        行1785 = 表1784 & 4294967295
                        列1786 = 表1784 >> 32
                    else:
                        键1783 = 句柄256(表744, 键863)
                        表1784 = 句柄256(表744, 键863 + 4)
                        行1785 = 表1784 & 255
                        列1786 = 表1784 >> 8
                    标记1170.append({'section': 目标1221['name'], 'offset': '0x%x' % 键1783, 'type': 行1785, 'symbol_index': 列1786})
                    if len(标记1170) >= 400:
                        return (标记1170, None)
    except Exception as 修补958:
        return (标记1170, 节点57(str(修补958), 60))
    return (标记1170, None)

def 参数441(变量720, 源780=6, limit=200):
    数据848 = 行265(变量720)
    if not 数据848.ok:
        return []
    文本708 = []
    try:
        with open(变量720, 'rb') as 构建915:
            for 目标1221 in 数据848.sections:
                if 目标1221['name'] not in ('.rodata', '.data', '.data.rel.ro', '.text'):
                    continue
                构建915.seek(目标1221['offset'])
                表744 = 构建915.read(min(目标1221['size'], 4 << 20))
                for 句柄776 in re.finditer(b'[\\x20-\\x7e]{%d,}' % 源780, 表744):
                    文本708.append(句柄776.group().decode('ascii', 'ignore'))
                    if len(文本708) >= limit:
                        return 文本708
    except Exception:
        pass
    return 文本708

def 结果442(键743):
    键63.head('ad components', 字节27)
    句柄1136 = 构建435(键743, [值1062 for 计数845 in 标记370.values() for 值1062 in 计数845], 'ads')
    if not 句柄1136:
        键63.info('no ad sdk classes found')
    队列1171 = {}
    for 映射852, 读取872 in 句柄1136.items():
        for 修补718, 计数845 in 标记370.items():
            if any((值1062.lower() in 映射852.lower() for 值1062 in 计数845)):
                队列1171.setdefault(修补718, []).append(读取872)
                break
    for 修补718 in sorted(队列1171):
        队列811 = 队列1171[修补718]
        键63.kv(修补718, '%d class(es)' % len(队列811), width=22)
        for 读取872 in 队列811[:3]:
            print('    ' + 打开33(路径46 + ' ' + 节点57(读取872['class'], 70)))
            if 读取872['init']:
                print('      ' + 打开33('init: ' + ', '.join(读取872['init'][:4])))
            if 读取872['show']:
                print('      ' + 打开33('show: ' + ', '.join(读取872['show'][:4])))
    键63.head('license components', 字节27)
    映射1172 = 构建435(键743, 读取432, 'license')
    if not 映射1172:
        键63.info('no license checker classes')
    for 映射852, 读取872 in list(映射1172.items())[:6]:
        键63.kv(节点57(映射852, 60), '%d method(s)' % len(读取872['methods']), width=62)
        if 读取872['methods']:
            print('    ' + 打开33('methods: ' + ', '.join(读取872['methods'][:6])))
    键63.head('billing components', 列26)
    条目1173 = 构建435(键743, 打开433, 'billing')
    if not 条目1173:
        键63.info('no billing client classes')
    for 映射852, 读取872 in list(条目1173.items())[:6]:
        键63.kv(节点57(映射852, 60), '%d method(s)' % len(读取872['methods']), width=62)
    键63.head('signature dependencies', 字节27)
    偏移1174 = 解析436(键743)
    if not 偏移1174:
        键63.ok('no class reads its own signing certificate')
    for 行785 in 偏移1174[:10]:
        键63.kv(节点57(行785['class'], 56), '%s · conf %.2f' % (行785['dex'], 行785['confidence']), width=58)
        print('    ' + 打开33(', '.join(行785['methods'][:5])))
    return {'ads': {名字989: [修补958['class'] for 修补958 in 步骤818] for 名字989, 步骤818 in 队列1171.items()}, 'license': list(映射1172.keys()), 'billing': list(条目1173.keys()), 'signature': 偏移1174}

def 缓存443(args):
    缓存3.probe()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    键743, 键1383 = 条目573(args.input)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    参数721 = 结果442(键743)
    if args.output:
        行105(Path(args.output).expanduser(), json.dumps(参数721, indent=2, default=str), 'w')
        键63.kv('written', str(args.output))
    return 0

def 索引444(状态849, 标记810, 标记850=None):
    值702 = ['Java.perform(function () {', '  var seen = {};', '  function hook(cls, meth, note) {', "    var key = cls + '#' + meth;", '    if (seen[key]) { return; }', '    seen[key] = true;', '    try {', '      var C = Java.use(cls);', '      C[meth].overloads.forEach(function (ov) {', '        ov.implementation = function () {', '          var args = Array.prototype.slice.call(arguments);', '          var ret = ov.apply(this, args);', '          send({ hook: key, note: note, args: args.map(String), ret: String(ret) });', '          return ret;', '        };', '      });', '    } catch (e) { send({ hook: key, error: String(e) }); }', '  }']
    for 区块1175 in 状态849:
        for 标记1490 in 区块1175.get('jni', []):
            cls = 标记1490['class'].replace('/', '.')
            if cls and 标记1490['method']:
                值702.append('  hook("%s", "%s", "%s");' % (cls, 标记1490['method'], 区块1175['object']))
    if 标记850:
        for 报告1199 in 标记850.get('candidates', []):
            cls = 报告1199['class'].strip('L;').replace('/', '.')
            for 读取1472 in 报告1199['methods'][:4]:
                值702.append('  hook("%s", "%s", "tls");' % (cls, 读取1472))
    值702 += ["  send({ script: 'arpxtool', apk: '%s', hooks: Object.keys(seen).length });" % 标记810, '});', '']
    return '\n'.join(值702)

def 计数445(args):
    缓存3.probe()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    键743, 键1383 = 条目573(args.input)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    报告839 = 打开273(键743, None)
    if not 报告839:
        键63.bad('no native objects in this archive')
        return 3
    键63.head('native objects', 字节27)
    for 修补958 in 报告839:
        节点697 = 修补958.summary()
        键63.kv(修补958.name, '%s · %d-bit · %s' % (节点697['machine'], 节点697['bits'], 表104(节点697['size'])), width=32)
        队列1491 = 报告439(修补958)
        if 队列1491:
            键63.kv('jni exports', len(队列1491), width=32)
            for 句柄776 in 队列1491[:6]:
                print('    ' + 打开33('%s -> %s#%s' % (节点57(句柄776['symbol'], 44), 句柄776['class'], 句柄776['method'])))
        标记1170, 名字709 = 变量440(修补958.path)
        if 标记1170:
            键63.kv('relocations', len(标记1170), width=32)
        elif 名字709:
            键63.kv('relocations', 名字709, width=32)
        if args.strings:
            打开1633 = 参数441(修补958.path, 6, args.strings)
            if 打开1633:
                键63.kv('strings', len(打开1633), width=32)
                for 报告1039 in 打开1633[:10]:
                    print('    ' + 打开33(路径46 + ' ' + 节点57(报告1039, 84)))
    if args.frida:
        状态849 = []
        for 修补958 in 报告839:
            状态849.append({'object': 修补958.name, 'jni': 报告439(修补958)})
        dest = Path(args.frida).expanduser()
        dest.parent.mkdir(parents=True, exist_ok=True)
        行105(dest, 索引444(状态849, 键743.name), 'w')
        键63.head('frida', 文本28)
        映射1492 = sum((len(名字909['jni']) for 名字909 in 状态849))
        键63.kv('hooks', 映射1492, width=18)
        键63.kv('written', str(dest))
        if 映射1492 == 0:
            键63.info('no jni exports found · the script is a skeleton to extend')
    return 0
路径446 = {'V': 'void', 'Z': 'true', 'I': 'zero', 'B': 'zero', 'S': 'zero', 'C': 'zero', 'F': 'zero', 'J': 'wide', 'D': 'wide'}
列表447 = {'ads': [值1062 for 计数845 in 标记370.values() for 值1062 in 计数845], 'license': 读取432, 'billing': 打开433}

def 数据448(区块815, 队列851):
    try:
        键863 = 区块815.p_off + 队列851 * 12
        条目1493 = 句柄256(区块815.d, 键863 + 4)
        return 区块815.type_name(条目1493)
    except Exception:
        return '?'

def 状态449(映射852):
    if not 映射852:
        return 'void'
    head = 映射852[0]
    if head == '[' or head == 'L':
        return 'null'
    return 路径446.get(head, 'null')

def 标记450(区块815, 表824):
    try:
        偏移1494 = 区块255(区块815.d, 区块815.m_off + 表824 * 8 + 2)
        return 数据448(区块815, 偏移1494)
    except Exception:
        return '?'

def 队列451(键743, 计数845, 行825=40000):
    句柄856 = {}
    句柄1176 = {}
    for 值1422, 参数721 in 关闭434(键743):
        区块815 = 写入311(参数721)
        if not 区块815.ok:
            continue
        区块1495 = {}
        for 句柄1496 in range(min(区块815.m_n, 400000)):
            try:
                cls = 区块815.type_name(区块255(参数721, 区块815.m_off + 句柄1496 * 8))
            except Exception:
                continue
            for 值1062 in 计数845:
                if 值1062.lower() in cls.lower():
                    区块1495[句柄1496] = cls
                    break
        if not 区块1495:
            continue
        源1140 = 0
        for 节点1497 in 构建395(值1422, 参数721, 20000, 行825):
            源1140 += 1
            if 源1140 > 行825:
                break
            for 值1142 in 节点1497.insns:
                if 值1142['kind'] != 'invoke' or 值1142['ref'] not in 区块1495:
                    continue
                节点1177 = '%s->%s' % (节点1497.descriptor, 节点1497.name)
                句柄856.setdefault(节点1177, set()).add(区块1495[值1142['ref']])
                句柄1176.setdefault(区块1495[值1142['ref']], set()).add(节点1177)
    return (句柄856, 句柄1176)

def 映射452(键743, 条目853, method_name):
    for 值1422, 参数721 in 关闭434(键743):
        区块815 = 写入311(参数721)
        if not 区块815.ok:
            continue
        名字829 = 区块815.find_class(条目853)
        if 名字829 is None:
            continue
        for 句柄1496 in range(min(区块815.m_n, 400000)):
            if 区块815.method_name(句柄1496) != method_name:
                continue
            if 区块815.type_name(区块255(参数721, 区块815.m_off + 句柄1496 * 8)) != 条目853:
                continue
            return 状态449(标记450(区块815, 句柄1496))
    return 'void'

def 条目453(name, 键703, 区块855):
    关闭1154 = []
    for 读取912, 修补958 in enumerate(区块855):
        关闭1154.append({'id': '%s-%d' % (name, 读取912), 'title': 修补958.get('title') or '%s target %d' % (name, 读取912), 'action': 'stub-method', 'targets': [修补958['target']], 'kind': 修补958.get('kind', 'void'), 'note': 修补958.get('note', '')})
    return {'schema': 'arp-patch/1', 'name': 键703, 'patches': 关闭1154, 'profiles': {'default': [值1062['id'] for 值1062 in 关闭1154]}}

def 偏移454(句柄856, 键743, limit=40):
    区块855 = []
    for 节点1177 in sorted(句柄856):
        if '->' not in 节点1177:
            continue
        映射852, 读取1472 = 节点1177.split('->', 1)
        行705 = 映射452(键743, 映射852, 读取1472)
        区块855.append({'target': '%s#%s' % (映射852.replace('/', '.').strip('L;'), 读取1472), 'kind': 行705, 'title': 'disable call site %s' % 读取1472, 'callees': sorted(句柄856[节点1177])[:4]})
        if len(区块855) >= limit:
            break
    return 区块855

def 区块455(键743):
    句柄816 = 构建435(键743, 列表447['ads'], 'ads')
    句柄856, 句柄1176 = 队列451(键743, 列表447['ads'])
    步骤1178 = {}
    for 映射852 in 句柄816:
        for 修补718, 计数845 in 标记370.items():
            if any((值1062.lower() in 映射852.lower() for 值1062 in 计数845)):
                步骤1178.setdefault(修补718, []).append(映射852)
                break
    区块855 = 偏移454(句柄856, 键743)
    栈1179 = 条目453('ads', 'ad integration call sites', 区块855)
    return {'networks': {名字989: len(步骤818) for 名字989, 步骤818 in 步骤1178.items()}, 'classes': len(句柄816), 'call_sites': len(句柄856), 'entries': 区块855, 'patchset': 栈1179}

def 句柄456(键743):
    句柄816 = 构建435(键743, 列表447['license'], 'license')
    句柄856, 句柄1176 = 队列451(键743, 列表447['license'])
    区块855 = 偏移454(句柄856, 键743)
    栈1179 = 条目453('license', 'license verification call sites', 区块855)
    return {'classes': len(句柄816), 'call_sites': len(句柄856), 'entries': 区块855, 'patchset': 栈1179}

def 节点457(键743):
    句柄816 = 构建435(键743, 列表447['billing'], 'billing')
    句柄856, 句柄1176 = 队列451(键743, 列表447['billing'])
    区块855 = 偏移454(句柄856, 键743)
    栈1179 = 条目453('billing', 'billing call sites', 区块855)
    return {'classes': len(句柄816), 'call_sites': len(句柄856), 'entries': 区块855, 'patchset': 栈1179}

def 步骤458(键743):
    偏移1174 = 解析436(键743)
    路径806 = []
    for 行785 in 偏移1174:
        for 句柄776 in 行785['methods']:
            if 句柄776 in 句柄136:
                行705 = 'true'
            elif 句柄776 in 节点137:
                行705 = 'false'
            else:
                行705 = 映射452(键743, 行785['class'], 句柄776)
            路径806.append({'target': '%s#%s' % (行785['class'].replace('/', '.').strip('L;'), 句柄776), 'kind': 行705, 'title': 'neutralise %s' % 句柄776})
    源1180 = 源460(键743)
    栈1179 = 条目453('signature', 'signature self-check methods', 路径806)
    return {'dependents': 偏移1174, 'targets': 路径806, 'native_refs': 源1180, 'patchset': 栈1179}
栈459 = ('signature', 'certificate', 'integrity', 'tamper', 'root', 'frida', 'xposed', 'debug', 'ptrace', 'check', 'verify', 'licen', 'billing')

def 源460(键743):
    文本708 = []
    for 修补958 in 打开273(键743, None):
        步骤978 = []
        for 状态1169 in list(修补958.imports) + list(getattr(修补958, 'symtab_names', [])):
            关闭1074 = 状态1169.lower()
            for 句柄776 in 栈459:
                if 句柄776 in 关闭1074:
                    步骤978.append(状态1169)
                    break
        值982 = 参数441(修补958.path, 5, 400)
        步骤1498 = [节点697 for 节点697 in 值982 if any((句柄776 in 节点697.lower() for 句柄776 in 栈459))]
        文本708.append({'object': 修补958.name, 'machine': 修补958.machine, 'bits': 修补958.bits, 'symbols': sorted(set(步骤978))[:20], 'strings': 步骤1498[:12]})
    return 文本708

def 目标461(键703, 节点857, 行705):
    键63.head(键703, 字节27)
    if 行705 == 'ads':
        if 节点857['networks']:
            for 修补718, 步骤698 in sorted(节点857['networks'].items()):
                键63.kv(修补718, '%d class(es)' % 步骤698, width=22)
        else:
            键63.info('no ad sdk detected')
    键63.kv('classes', 节点857.get('classes', 0), width=22)
    键63.kv('call sites', 节点857.get('call_sites', len(节点857.get('targets', []))), width=22)
    区块855 = 节点857.get('entries') or 节点857.get('targets') or []
    for 修补958 in 区块855[:10]:
        键63.bullet('%s  ·  %s' % (修补958['target'], 修补958.get('kind')))
    if len(区块855) > 10:
        键63.info('… %d more' % (len(区块855) - 10))
    if not 区块855:
        键63.info('nothing to target')

def 值462(args, 行705):
    缓存3.probe()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    键743, 键1383 = 条目573(args.input)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    if 行705 == 'ads':
        节点857 = 区块455(键743)
        目标461('advertising manager', 节点857, 'ads')
    elif 行705 == 'license':
        节点857 = 句柄456(键743)
        目标461('license manager', 节点857, 'license')
    elif 行705 == 'billing':
        节点857 = 节点457(键743)
        目标461('billing manager', 节点857, 'billing')
    elif 行705 == 'signature':
        节点857 = 步骤458(键743)
        目标461('signature manager', 节点857, 'signature')
        if 节点857['native_refs']:
            键63.head('native protection references', 列26)
            for 名字909 in 节点857['native_refs']:
                键63.kv(名字909['object'], '%s · %d symbol(s) · %d string(s)' % (名字909['machine'], len(名字909['symbols']), len(名字909['strings'])), width=28)
                for 节点697 in 名字909['symbols'][:4]:
                    print('    ' + 打开33(路径46 + ' ' + 节点57(节点697, 76)))
    else:
        键63.bad('unknown module')
        return 2
    栈1179 = 节点857.get('patchset') or {'patches': []}
    条目1053 = Path(args.output).expanduser() if args.output else HOME
    if 条目1053.suffix:
        条目1053 = 条目1053.parent
    条目1053.mkdir(parents=True, exist_ok=True)
    目标1181 = 条目1053 / ('%s-%s.patch.json' % (键743.stem, 行705))
    行105(目标1181, json.dumps(栈1179, indent=2), 'w')
    键63.head('generated patch set', 文本28)
    键63.kv('patches', len(栈1179['patches']))
    键63.kv('file', str(目标1181))
    if 栈1179['patches'] and args.dry_run:
        键63.info('dry run · apply with: --patch ' + str(目标1181))
    if 栈1179['patches'] and (not args.dry_run):
        结果842 = [{'id': 值1062['id'], 'title': 值1062['title'], 'action': 'stub-method', 'targets': 值1062['targets'], 'kind': 值1062['kind'], 'conflicts': [], 'note': 值1062.get('note', '')} for 值1062 in 栈1179['patches']]
        report = 行425(结果842, 键743)
        ok = [名字909 for 名字909 in report if 名字909['ok']]
        键63.head('apply', 文本28)
        键63.kv('resolved', '%d of %d' % (len(ok), len(report)))
        if not ok:
            键63.bad('no target resolved · nothing applied')
            return 5
        表1184 = 映射572(键743, 行705)
        变量1160, 名字709 = 列426(键743, 表1184, [映射1132 for 映射1132 in 结果842 if any((名字909['id'] == 映射1132['id'] and 名字909['ok'] for 名字909 in report))], 缓存843=str(表1184) + '.backup')
        if 变量1160 is None:
            键63.bad(名字709)
            return 6
        栈1499 = Path(str(表1184) + '.journal.json')
        行105(栈1499, json.dumps(变量1160, indent=2), 'w')
        键63.ok('applied %d patch group(s)' % len(变量1160['applied']))
        键63.kv('output', str(表1184))
        键63.kv('journal', str(栈1499))
        if args.sign:
            映射772, 检查1390 = 缓存203({'zipalign': 字节107('zipalign')}, 表1184, 表1184.parent)
            源1500, 目标1501 = 路径206(构建195(表1184.parent, allow_net=False, 缓存723=True), 表1184, 表1184.parent, args.password)
            键63.kv('signed', 目标1501 if 源1500 else 'no signer available')
    return 0

def 键463(args):
    缓存3.probe()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    键743, 键1383 = 条目573(args.input)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    值1182 = []
    键63.head('full modification', 行25)
    for 行705, 表1344 in (('ads', 区块455), ('license', 句柄456), ('billing', 节点457), ('signature', 步骤458)):
        try:
            字节827 = 表1344(键743)
        except Exception as 修补958:
            键63.warn('%s · %s' % (行705, 节点57(str(修补958), 60)))
            continue
        步骤698 = len(字节827.get('patchset', {}).get('patches', []))
        值1182.append((行705, 字节827))
        键63.kv(行705, '%d target(s)' % 步骤698, width=16)
    列表767 = {'schema': 'arp-patch/1', 'name': 'full-modification', 'patches': [], 'profiles': {}}
    for 行705, 字节827 in 值1182:
        列表767['patches'].extend(字节827.get('patchset', {}).get('patches', []))
    列表767['profiles']['all'] = [值1062['id'] for 值1062 in 列表767['patches']]
    条目1053 = Path(args.output).expanduser() if args.output else HOME
    if 条目1053.suffix:
        条目1053 = 条目1053.parent
    条目1053.mkdir(parents=True, exist_ok=True)
    变量720 = 条目1053 / ('%s-full.patch.json' % 键743.stem)
    行105(变量720, json.dumps(列表767, indent=2), 'w')
    键63.head('merged patch set', 文本28)
    键63.kv('patches', len(列表767['patches']))
    键63.kv('file', str(变量720))
    if args.dry_run:
        键63.info('dry run · nothing applied')
        return 0
    结果842 = [{'id': 值1062['id'], 'title': 值1062['title'], 'action': 'stub-method', 'targets': 值1062['targets'], 'kind': 值1062['kind'], 'conflicts': [], 'note': 值1062.get('note', '')} for 值1062 in 列表767['patches']]
    if not 结果842:
        键63.bad('nothing to apply')
        return 5
    report = 行425(结果842, 键743)
    键1183 = [映射1132 for 映射1132 in 结果842 if any((名字909['id'] == 映射1132['id'] and 名字909['ok'] for 名字909 in report))]
    键63.kv('resolved', '%d of %d' % (len(键1183), len(report)))
    if not 键1183:
        return 5
    表1184 = 映射572(键743, 'modified')
    变量1160, 名字709 = 列426(键743, 表1184, 键1183, 缓存843=str(表1184) + '.backup')
    if 变量1160 is None:
        键63.bad(名字709)
        return 6
    行105(Path(str(表1184) + '.journal.json'), json.dumps(变量1160, indent=2), 'w')
    键63.ok('applied %d change group(s)' % len(变量1160['applied']))
    映射772, 检查1390 = 缓存203({'zipalign': 字节107('zipalign')}, 表1184, 表1184.parent)
    源1500, 目标1501 = 路径206(构建195(表1184.parent, allow_net=False, 缓存723=True), 表1184, 表1184.parent, args.password)
    键63.kv('output', str(表1184))
    键63.kv('signed', 目标1501 if 源1500 else 'no signer available')
    目标301(表1184)
    return 0
表464 = {'aarch64': bytes.fromhex('00008052c0035fd6'), 'arm': bytes.fromhex('00207047'), 'x86_64': bytes.fromhex('31c0c3'), 'x86': bytes.fromhex('31c0c3'), 'riscv': bytes.fromhex('1305000067800000')}

def 行465(数据848, 步骤858):
    for 值1502, 键1503, 表1504 in getattr(数据848, 'segments', []):
        if 值1502 <= 步骤858 < 值1502 + 表1504:
            return 键1503 + (步骤858 - 值1502)
    return None

def 列466(数据848, 栈859):
    try:
        with open(数据848.path, 'rb') as 构建915:
            for 目标1221 in 数据848.sections:
                if 目标1221['type'] not in (2, 11):
                    continue
                缓存1603 = 目标1221['link']
                if not 0 <= 缓存1603 < len(数据848.sections):
                    continue
                索引1604 = 数据848.sections[缓存1603]
                构建915.seek(索引1604['offset'])
                计数1605 = 构建915.read(min(索引1604['size'], 4 << 20))
                扫描917 = 目标1221['entsize'] or (24 if 数据848.bits == 64 else 16)
                列866 = min(目标1221['size'] // 扫描917 if 扫描917 else 0, 80000)
                构建915.seek(目标1221['offset'])
                表744 = 构建915.read(扫描917 * 列866)
                for 读取912 in range(列866):
                    键863 = 读取912 * 扫描917
                    if 键863 + 扫描917 > len(表744):
                        break
                    值1702 = 句柄256(表744, 键863)
                    if not 值1702 or 值1702 >= len(计数1605):
                        continue
                    name = 计数1605[值1702:].split(b'\x00')[0].decode('ascii', 'ignore')
                    if name != 栈859:
                        continue
                    if 数据848.bits == 64:
                        标记730 = struct.unpack_from('<Q', 表744, 键863 + 8)[0]
                    else:
                        标记730 = 句柄256(表744, 键863 + 4)
                    if 标记730 == 0:
                        continue
                    行745 = 行465(数据848, 标记730 & ~1)
                    return 行745
    except Exception:
        return None
    return None

def 字节467(变量720, 栈859, dry=False):
    数据848 = 行265(变量720)
    if not 数据848.ok:
        return (False, 'not an elf object', None)
    结果1122 = 表464.get(数据848.machine)
    if not 结果1122:
        return (False, 'no stub for isa ' + 数据848.machine, None)
    行745 = 列466(数据848, 栈859)
    if 行745 is None:
        return (False, 'symbol not found', None)
    try:
        with open(变量720, 'rb') as 构建915:
            构建915.seek(行745)
            键783 = 构建915.read(len(结果1122))
        if 键783 == 结果1122:
            return (True, 'already stubbed', {'offset': '0x%x' % 行745, 'symbol': 栈859, 'arch': 数据848.machine})
        if not dry:
            计数1165 = Path(str(变量720) + '.arpbak')
            if not 计数1165.exists():
                shutil.copy2(变量720, 计数1165)
            with open(变量720, 'r+b') as 构建915:
                构建915.seek(行745)
                构建915.write(结果1122)
            with open(变量720, 'rb') as 构建915:
                构建915.seek(行745)
                if 构建915.read(len(结果1122)) != 结果1122:
                    if 计数1165.exists():
                        shutil.copy2(计数1165, 变量720)
                    return (False, 'write verification failed', None)
        return (True, 'stubbed', {'offset': '0x%x' % 行745, 'symbol': 栈859, 'arch': 数据848.machine})
    except Exception as 修补958:
        return (False, 节点57(str(修补958), 60), None)

def 文本468(args):
    缓存3.probe()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    键743, 键1383 = 条目573(args.input)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    行1185 = [节点697.strip() for 节点697 in args.native_patch.split(',') if 节点697.strip()]
    if not 行1185:
        键63.bad('no symbol given')
        return 2
    报告839 = 打开273(键743, None)
    if not 报告839:
        键63.bad('no native objects')
        return 3
    文本708 = Path(args.output).expanduser() if args.output else 映射572(键743, 'native')
    写入751 = Path(tempfile.mkdtemp(扫描717='arp_nat_'))
    偏移1134 = []
    try:
        for 修补958 in 报告839:
            for 状态1169 in 行1185:
                ok, 结果922, info = 字节467(修补958.path, 状态1169, dry=args.dry_run)
                if ok and info:
                    偏移1134.append((修补958.name, 状态1169, 结果922, info))
                    键63.ok('%s · %s · %s' % (修补958.name, 状态1169, info['offset']))
                elif 'not found' not in 结果922:
                    键63.warn('%s · %s · %s' % (修补958.name, 状态1169, 结果922))
        if not 偏移1134 or args.dry_run:
            键63.info('no archive written')
            return 0
        with zipfile.ZipFile(键743) as 名字1429, zipfile.ZipFile(文本708, 'w') as 检查1430:
            for 区块1415 in 名字1429.infolist():
                if 区块1415.filename.upper().startswith('META-INF/') and 区块1415.filename.upper().endswith(('.SF', '.RSA', '.DSA', '.EC', '.MF')):
                    continue
                参数761 = 名字1429.read(区块1415.filename)
                for 修补958 in 报告839:
                    if 区块1415.filename.endswith('/' + 修补958.name) or 区块1415.filename == 修补958.name:
                        参数761 = Path(修补958.path).read_bytes()
                        break
                状态1609 = zipfile.ZipInfo(区块1415.filename, date_time=区块1415.date_time)
                状态1609.compress_type = 区块1415.compress_type
                状态1609.external_attr = 区块1415.external_attr
                状态1609.internal_attr = 区块1415.internal_attr
                状态1609.create_system = 区块1415.create_system
                检查1430.writestr(状态1609, 参数761)
        映射772, 检查1390 = 缓存203({'zipalign': 字节107('zipalign')}, 文本708, 文本708.parent)
        键63.head('result', 文本28)
        键63.kv('patched', '%d symbol(s)' % len(偏移1134))
        键63.kv('output', str(文本708))
        if args.sign:
            源1500, 目标1501 = 路径206(构建195(写入751, allow_net=False, 缓存723=True), 文本708, 写入751, args.password)
            键63.kv('signed', 目标1501 if 源1500 else 'no signer available')
        目标301(文本708)
        return 0
    finally:
        shutil.rmtree(写入751, ignore_errors=True)
名字469 = {'ssl': ['-m', 'ssl'], 'signature': ['-m', 'signature'], 'security': ['-m', 'security'], 'full': ['-m', 'full'], 'fast': ['-m', 'fast'], 'surgery': ['-m', 'surgery'], 'native': ['-m', 'native'], 're': ['-m', 're'], 'report': ['-m', 're'], 'unpack': ['-m', 'unpack'], 'inspect': ['-m', 'inspect'], 'verify': ['-m', 'verify'], 'detect': ['-m', 'detect'], 'ads': ['--ads-manager'], 'license': ['--license-manager'], 'billing': ['--billing-manager'], 'signature-manager': ['--signature-manager'], 'install': ['--install-check'], 'components': ['--components'], 'cert': ['--cert'], 'native-analysis': ['--native-analysis'], 'full-modification': ['--full-modification'], 'security-test': ['--security-test'], 'self-check': ['--self-check'], 'install-cli': ['--install-cli'], 'edit': ['--edit'], 'ssl-engine': ['--ssl-engine'], 'signature-engine': ['--signature-engine'], 'so-report': ['--so-report'], 'secrets': ['--secrets'], 'arsc': ['--arsc'], 'axml2xml': ['--axml2xml'], 'xml2axml': ['--xml2axml'], 'hex': ['--hex'], 'clone': ['--clone'], 'compare-dex': ['--compare-dex'], 'vdex': ['--vdex'], 'dex-edit': ['--dex-edit'], 'sign-native': ['--sign-native'], 'tools': ['--tools'], 'flutter-ssl': ['--flutter-ssl'], 'flutter': ['--flutter-ssl'], 'setup': ['--setup'], 'install-all': ['--install-all'], 'provenance': ['--provenance'], 'repair': ['--repair'], 'keygen': ['--keygen'], 'keygen-app': ['--keygen-app'], 'identify': ['--identify'], 'diagnose': ['--diagnose'], 'exit-check': ['--exit-check'], 'crash-read': ['--crash-read'], 'crashpatch': ['--crashpatch'], 'axml-info': ['--axml-info'], 'fix-native': ['--fix-native'], 'crashinject': ['--crashinject'], 'logcat': ['--logcat'], 'crash': ['--exit-check'], 'sign': ['--sign-apk'], 'key': ['--keygen'], 'fix': ['--repair'], 'doctor': ['--doctor'], 'clean': ['--clean']}
检查470 = {'patch': ['--patch'], 'revert': ['--revert'], 'methods': ['--methods'], 'search': ['--search'], 'compare': ['--compare'], 'targets': ['--targets'], 'rules': ['--rules'], 'native-patch': ['--native-patch'], 'edit': ['--edit'], 'ssl-engine': ['--ssl-engine'], 'signature-engine': ['--signature-engine'], 'so-report': ['--so-report'], 'secrets': ['--secrets'], 'arsc': ['--arsc'], 'axml2xml': ['--axml2xml'], 'xml2axml': ['--xml2axml'], 'hex': ['--hex'], 'clone': ['--clone'], 'compare-dex': ['--compare-dex'], 'vdex': ['--vdex'], 'dex-edit': ['--dex-edit'], 'sign-native': ['--sign-native'], 'tools': ['--tools'], 'flutter-ssl': ['--flutter-ssl'], 'flutter': ['--flutter-ssl'], 'setup': ['--setup'], 'install-all': ['--install-all'], 'provenance': ['--provenance'], 'repair': ['--repair'], 'embed-ca': ['--embed-ca']}
写入471 = ('.apk', '.apks', '.xapk', '.apkm', '.aab', '.ipa', '.dex', '.so', '.zip', '.jar', '.aar')
读取472 = ('install-cli', 'doctor', 'clean', 'self-check', 'tools', 'setup', 'install-all', 'provenance', 'keygen', 'logcat')

def 打开473(源860):
    关闭1074 = 源860.lower()
    return 关闭1074.endswith(写入471) or Path(源860).expanduser().exists()

def 关闭474(列706):
    if not 列706:
        return ([], 'reference')
    head = 列706[0].lower()
    if head in ('help', '/help', '-h', '--help', '?', 'commands'):
        return ([], 'reference')
    if head in 读取472:
        return (名字469[head] + 列706[1:], None)
    if head in 名字469 and len(列706) > 1 and 打开473(列706[1]):
        return (['-i', 列706[1]] + 名字469[head] + 列706[2:], None)
    if not 打开473(列706[0]):
        return (列706, None)
    列1186 = 列706[1:]
    文本708 = ['-i', 列706[0]]
    if 列1186:
        结果762 = 列1186[0].lower()
        if 结果762 in 名字469:
            文本708 += 名字469[结果762]
            列1186 = 列1186[1:]
        elif 结果762 in 检查470:
            if len(列1186) < 2:
                return (文本708, ('missing-arg', 结果762))
            文本708 += 检查470[结果762] + [列1186[1]]
            列1186 = 列1186[2:]
    return (文本708 + 列1186, None)
构建475 = [('core', 行25, [('ssl', 'neutralise tls verification and trust managers'), ('signature', 'neutralise signature self-checks'), ('security', 'root, vpn, frida and emulator checks'), ('full', 'binary + bytecode + manifest + sign'), ('fast', 'manifest and netsec only, never smali'), ('surgery', 'no java, no apktool, no aapt2'), ('native', 'binary only, surgical repack')]), ('analysis', 列26, [('re', 'decompile and deep static analysis'), ('detect', 'ads, billing, license, signature map'), ('inspect', 'read only forensic report'), ('verify', 'signature and archive audit'), ('install', 'why an archive would refuse to install'), ('components', 'ad, license, billing, signature components'), ('native-analysis', 'elf, jni, relocations, strings'), ('security-test', 'nine stage defensive audit')]), ('modification', 字节27, [('ads', 'detect and disable ad call sites'), ('license', 'detect and disable license call sites'), ('billing', 'detect and disable billing call sites'), ('signature-manager', 'signature dependency and self checks'), ('full-modification', 'every manager merged and applied'), ('patch', 'apply a json patch set'), ('revert', 'restore from a journal'), ('unpack', 'extract every entry byte for byte')]), ('tools', 文本28, [('methods', 'list dex methods matching a regex'), ('search', 'search strings across dex and assets'), ('cert', 'signing certificate facts'), ('compare', 'diff two archives'), ('native-patch', 'stub native symbols in every .so'), ('clean', 'purge stale work trees'), ('doctor', 'diagnose the host and toolchain'), ('self-check', 'run internal diagnostics')])]
解析476 = [('-i, --input PATH', 'target archive'), ('-o, --output PATH', 'where to write the result'), ('-m, --mode NAME', 'operation mode'), ('--targets FILE', 'user patch list, Class#method kind'), ('--rules FILE', 'json or yaml detection rules'), ('--patch FILE', 'json patch set'), ('--profile NAME', 'patch profile'), ('--dry-run', 'plan only, never write'), ('--apply', 'kept for compatibility, apply is default'), ('--sign', 'sign the result'), ('--unsigned', 'skip signing'), ('--embed-ca PEM', 'trust your own ca certificate'), ('--engine VERSION', 'force an apktool version'), ('--flutter-engine SO', 'drop-in libflutter.so (prebuilt patched engine)'), ('--remove-license', 'neutralise play store licence checks'), ('--max-engines N', 'how many engines to try'), ('--resume DIR', 'rebuild from a preserved tree'), ('--baseline APK', 'earlier build to diff against'), ('--java DIR', 'decompile to java with jadx'), ('--disasm N', 'disassemble native instructions'), ('--frida FILE', 'write a frida hook script'), ('--mapping FILE', 'proguard mapping'), ('--batch DIR', 'process a folder'), ('--no-net', 'never download anything'), ('--no-anim', 'disable animation'), ('--quiet', 'skip the banner'), ('--keep', 'keep the work tree'), ('--log FILE', 'session log path')]

def 扫描477():
    缓存3.probe()
    节点97(not 缓存3.enabled)
    print()
    print('  ' + 栈59('usage', 行25, True))
    print('  ' + 索引4(区块15, True)('first run:  ') + 修补38('python3 arpxtool.py install-cli') + 打开33('   installs the arpxtool launcher'))
    print()
    print('  ' + 修补38('arpxtool <archive> <command> [flags]') + 打开33('        positional form'))
    print('  ' + 修补38('arpxtool -i <archive> -m <mode> [flags]') + 打开33('      flag form'))
    print('  ' + 修补38('arpxtool') + 打开33('                             this screen'))
    print('  ' + 修补38('arpxtool --menu') + 打开33('                      interactive selector'))
    for 键703, 句柄696, 打开793 in 构建475:
        print()
        print('  ' + 目标61(缓存3.clamp(20, 74), 句柄696, 索引44))
        print('  ' + 索引4(句柄696[-1], True)(键703.upper()))
        print('  ' + 目标61(缓存3.clamp(20, 74), 句柄696, 索引44))
        for name, 映射852 in 打开793:
            print('  ' + 索引4(句柄696[0])(name.ljust(20)) + 打开33(映射852))
    print()
    print('  ' + 目标61(缓存3.clamp(20, 74), 列26, 索引44))
    print('  ' + 索引4(标记10, True)('FLAGS'))
    print('  ' + 目标61(缓存3.clamp(20, 74), 列26, 索引44))
    for name, 映射852 in 解析476:
        print('  ' + 修补38(name.ljust(24)) + 打开33(映射852))
    print()
    print('  ' + 目标61(缓存3.clamp(20, 74), 文本28, 索引44))
    print('  ' + 索引4(节点17, True)('EXAMPLES'))
    print('  ' + 目标61(缓存3.clamp(20, 74), 文本28, 索引44))
    for 计数885 in ('arpxtool app.apk ssl', 'arpxtool app.apk signature --sign', 'arpxtool app.apk ads', 'arpxtool app.apk detect', 'arpxtool app.apk install', 'arpxtool app.apk patch my.patch.json', 'arpxtool app.apk methods license', 'arpxtool app.apk compare old.apk', 'arpxtool app.apk unpack ./out', 'arpxtool app.apk security-test --rules custom_rules.example.json'):
        print('  ' + 打开33('$ ') + 修补38(计数885))
    print()
    print('  ' + 目标61(缓存3.clamp(20, 74), 行25))
    return 0

def 修补478():
    字节1187 = []
    扫描717 = os.environ.get('PREFIX')
    if 扫描717:
        字节1187.append(Path(扫描717) / 'bin')
    字节1187.append(Path('/data/data/com.termux/files/usr/bin'))
    字节1187.append(HOME / '.local' / 'bin')
    字节1187.append(HOME / 'bin')
    句柄1096 = []
    for 行785 in 字节1187:
        if 行785 not in 句柄1096:
            句柄1096.append(行785)
    return 句柄1096

def 报告479(args):
    缓存3.probe()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    键63.head('install launcher', 行25)
    文本1188 = Path(sys.argv[0]).resolve()
    if not 文本1188.exists():
        文本1188 = Path(__file__).resolve()
    键63.kv('script', str(文本1188))
    name = args.install_cli if isinstance(args.install_cli, str) and args.install_cli else 'arpxtool'
    列表847 = '#!/usr/bin/env sh\nexec python3 %s "$@"\n' % 变量480(str(文本1188))
    名字1189 = None
    for 行785 in 修补478():
        try:
            行785.mkdir(parents=True, exist_ok=True)
        except Exception:
            continue
        关闭794 = 行785 / name
        try:
            行105(关闭794, 列表847, 'w')
            os.chmod(关闭794, 493)
            名字1189 = 关闭794
            break
        except Exception:
            continue
    if not 名字1189:
        键63.bad('no writable bin directory found')
        return 3
    键63.ok('launcher written · ' + str(名字1189))
    检查1190 = os.environ.get('PATH', '')
    if str(名字1189.parent) in 检查1190.split(':'):
        键63.ok('directory is already on PATH · type: ' + name)
    else:
        键63.warn(str(名字1189.parent) + ' is not on PATH')
        键63.info('add it: export PATH="' + str(名字1189.parent) + ':$PATH"')
    写入1191 = shutil.which(name)
    if 写入1191 and Path(写入1191) != 名字1189:
        键63.warn("another '" + name + "' resolves first · " + 写入1191)
        if os.environ.get('PREFIX'):
            键63.info('on termux $PREFIX/bin normally comes before /system/bin')
            键63.info('open a new shell, then run: hash -r; which arp')
        键63.info('if the system tool still wins, install under another name:')
        键63.info('  python3 ' + 文本1188.name + ' install-cli arpx')
    键63.head('check', 文本28)
    for probe in (name,):
        键63.kv(probe, shutil.which(probe) or 'not resolved yet')
    键63.info('open a new shell if the command is not found yet')
    return 0

def 变量480(标记730):
    if not 标记730:
        return "''"
    if re.fullmatch('[A-Za-z0-9_./@%+=:,-]+', 标记730):
        return 标记730
    return "'" + 标记730.replace("'", '\'"\'"\'') + "'"
参数481 = ('netsec_mode', 'threads', 'timeout', 'password', 'max_engines', 'unsigned', 'sign', 'embed_ca', 'no_net', 'no_anim', 'quiet', 'keep', 'strategy', 'engine')

def 结果482(args):
    变量720 = getattr(args, 'config', None)
    if not 变量720:
        return args
    状态729 = Path(变量720).expanduser()
    if not 状态729.exists():
        键63.warn('config not found · ' + str(状态729))
        return args
    try:
        参数721 = json.loads(状态729.read_text(encoding='utf-8'))
    except Exception as 修补958:
        键63.warn('config unreadable · ' + 节点57(str(修补958), 60))
        return args
    if not isinstance(参数721, dict):
        键63.warn('config must be a json object, got ' + type(参数721).__name__)
        return args
    栈979 = []
    for key, 标记730 in 参数721.items():
        变量1480 = str(key).replace('-', '_')
        if 变量1480 not in 参数481 or not hasattr(args, 变量1480):
            continue
        current = getattr(args, 变量1480)
        if current in (None, False, 0, 'auto', 'user'):
            setattr(args, 变量1480, 标记730)
            栈979.append(变量1480)
    if 栈979:
        键63.info('config applied · ' + ', '.join(栈979))
    if getattr(args, 'threads', None):
        表184['threads'] = args.threads
    if getattr(args, 'timeout', None):
        表184['timeout'] = args.timeout
    return args
缓存483 = set(range(50, 62))
索引484 = {40, 41, 42}
计数485 = {18, 19, 20, 21, 22, 23, 24, 25}
路径486 = 0

def 列表487(参数721, 条目853, method_name):
    区块815 = 写入311(参数721)
    if not 区块815.ok:
        return None
    名字829 = 区块815.find_class(条目853)
    if 名字829 is None:
        return None
    目标1141 = 句柄256(参数721, 名字829 + 24)
    if not 目标1141:
        return None
    值1062 = 目标1141
    try:
        索引1444, 值1062 = 步骤258(参数721, 值1062)
        计数1445, 值1062 = 步骤258(参数721, 值1062)
        路径1446, 值1062 = 步骤258(参数721, 值1062)
        列表1447, 值1062 = 步骤258(参数721, 值1062)
        for 读取1112 in range(索引1444 + 计数1445):
            读取1112, 值1062 = 步骤258(参数721, 值1062)
            读取1112, 值1062 = 步骤258(参数721, 值1062)
        for 列866 in (路径1446, 列表1447):
            结果882 = 0
            for 读取1112 in range(列866):
                文本1108, 值1062 = 步骤258(参数721, 值1062)
                结果882 += 文本1108
                读取1112, 值1062 = 步骤258(参数721, 值1062)
                栈819, 值1062 = 步骤258(参数721, 值1062)
                if 栈819 and 区块815.method_name(结果882) == method_name:
                    return 栈819
    except Exception:
        return None
    return None

def 数据488(目标861, 值862=None):
    if 值862 == 18:
        return 目标861 >> 8 & 15
    return 目标861 >> 8 & 255

def 状态489(参数721, 键863, 表864, 值862):
    if 值862 == 18:
        修补1318 = 区块255(参数721, 键863 + 表864 * 2)
        行1505 = 修补1318 >> 12 & 15
        return 行1505 - 16 if 行1505 & 8 else 行1505
    if 值862 == 19:
        步骤818 = 区块255(参数721, 键863 + (表864 + 1) * 2)
        return 检查390(步骤818)
    if 值862 == 20:
        步骤818 = 区块255(参数721, 键863 + (表864 + 1) * 2) << 16 | 区块255(参数721, 键863 + (表864 + 2) * 2)
        return 写入391(步骤818)
    if 值862 == 21:
        return 区块255(参数721, 键863 + (表864 + 1) * 2) << 16
    return None

def 标记490(参数721, 键863, 表864, 值862, 标记730):
    读取1192 = 数据488(区块255(参数721, 键863 + 表864 * 2), 值862)
    if 值862 == 18:
        if not -8 <= 标记730 <= 7:
            return False
        行1505 = 标记730 & 15
        struct.pack_into('<H', 参数721, 键863 + 表864 * 2, 18 | 读取1192 << 8 | 行1505 << 12)
        return True
    if 值862 == 19:
        if not -32768 <= 标记730 <= 32767:
            return False
        struct.pack_into('<H', 参数721, 键863 + (表864 + 1) * 2, 标记730 & 65535)
        return True
    if 值862 == 20:
        struct.pack_into('<H', 参数721, 键863 + (表864 + 1) * 2, 标记730 >> 16 & 65535)
        struct.pack_into('<H', 参数721, 键863 + (表864 + 2) * 2, 标记730 & 65535)
        return True
    if 值862 == 21:
        if 标记730 & 65535:
            return False
        struct.pack_into('<H', 参数721, 键863 + (表864 + 1) * 2, 标记730 >> 16 & 65535)
        return True
    return False

def 队列491(参数721, 键863, 表864, 值862, 行865):
    if 值862 in 缓存483:
        偏移894 = 区块255(参数721, 键863 + (表864 + 1) * 2)
        if 行865:
            struct.pack_into('<H', 参数721, 键863 + 表864 * 2, 41)
            struct.pack_into('<H', 参数721, 键863 + (表864 + 1) * 2, 偏移894)
        else:
            struct.pack_into('<H', 参数721, 键863 + 表864 * 2, 路径486)
            struct.pack_into('<H', 参数721, 键863 + (表864 + 1) * 2, 路径486)
        return True
    if 值862 == 40:
        if 行865:
            return True
        struct.pack_into('<H', 参数721, 键863 + 表864 * 2, 路径486)
        return True
    if 值862 == 41:
        if 行865:
            return True
        struct.pack_into('<H', 参数721, 键863 + 表864 * 2, 路径486)
        struct.pack_into('<H', 参数721, 键863 + (表864 + 1) * 2, 路径486)
        return True
    return False

def 映射492(参数721, 键863, 表864, 列866, 字节867):
    for 名字989 in range(表864, min(表864 + 列866, 字节867)):
        struct.pack_into('<H', 参数721, 键863 + 名字989 * 2, 路径486)

class 条目493:

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

def 偏移494(参数721, 数据808):
    计数805 = bytearray(参数721)
    节点857 = 条目493()
    for 打开1193 in 数据808:
        action = str(打开1193.get('action', '')).lower()
        cls = 打开1193.get('class')
        读取1472 = 打开1193.get('method')
        if action == 'stub':
            行705 = str(打开1193.get('kind', 'true')).lower()
            关闭794 = [(计数365(cls), 读取1472, 行705)] if cls and 读取1472 else []
            if 关闭794:
                文本708, 步骤978 = 映射332(bytes(计数805), 关闭794)
                if 步骤978:
                    计数805 = bytearray(文本708)
                    节点857.ok('stub %s#%s -> %s' % (cls, 读取1472, 行705))
                else:
                    节点857.skip('stub %s#%s not found' % (cls, 读取1472))
            continue
        if not (cls and 读取1472):
            节点857.fail('%s needs class and method' % action)
            continue
        栈819 = 列表487(bytes(计数805), 计数365(cls), 读取1472)
        if 栈819 is None:
            节点857.skip('%s#%s not found' % (cls, 读取1472))
            continue
        字节867 = 句柄256(计数805, 栈819 + 12)
        键863 = 栈819 + 16
        表864 = int(打开1193.get('at', 0))
        if 表864 < 0 or 表864 >= 字节867:
            节点857.fail('%s#%s pc %d out of range' % (cls, 读取1472, 表864))
            continue
        值862 = 区块255(计数805, 键863 + 表864 * 2) & 255
        if action == 'nop':
            列866 = int(打开1193.get('count', 1))
            映射492(计数805, 键863, 表864, 列866, 字节867)
            节点857.ok('nop %s#%s pc %d x%d' % (cls, 读取1472, 表864, 列866))
        elif action == 'const':
            标记730 = int(打开1193.get('value', 0))
            if 值862 in 计数485 and 标记490(计数805, 键863, 表864, 值862, 标记730):
                节点857.ok('const %s#%s pc %d -> %d' % (cls, 读取1472, 表864, 标记730))
            else:
                节点857.skip('const %s#%s pc %d op 0x%02x not writable' % (cls, 读取1472, 表864, 值862))
        elif action == 'branch':
            行865 = bool(打开1193.get('take', True))
            if 队列491(计数805, 键863, 表864, 值862, 行865):
                节点857.ok('branch %s#%s pc %d -> %s' % (cls, 读取1472, 表864, 'taken' if 行865 else 'never'))
            else:
                节点857.skip('branch %s#%s pc %d op 0x%02x not a branch' % (cls, 读取1472, 表864, 值862))
        else:
            节点857.fail('unknown action ' + action)
    if 节点857.applied:
        打开313(计数805)
    return (计数805, 节点857)

def 区块495(变量720):
    状态729 = Path(变量720).expanduser()
    if not 状态729.exists():
        return (None, 'edit file not found')
    try:
        参数721 = json.loads(状态729.read_text(encoding='utf-8'))
    except Exception as 修补958:
        return (None, 'json parse error: ' + 节点57(str(修补958), 60))
    if isinstance(参数721, dict):
        数据808 = 参数721.get('edits') or []
    elif isinstance(参数721, list):
        数据808 = 参数721
    else:
        return (None, "expected a list or an object with 'edits'")
    if not isinstance(数据808, list):
        return (None, "'edits' must be a list")
    return (数据808, None)

def 句柄496(键743, 文本708, 数据808):
    偏移1134 = 条目493()
    键1103 = False
    try:
        with zipfile.ZipFile(键743) as 名字1429:
            修补798 = {}
            for name in 名字1429.namelist():
                if not re.match('classes\\d*\\.dex$', name):
                    continue
                计数805, 字节827 = 偏移494(名字1429.read(name), 数据808)
                偏移1134.applied.extend(('%s: %s' % (name, 队列691) for 队列691 in 字节827.applied))
                偏移1134.skipped.extend(('%s: %s' % (name, 节点697) for 节点697 in 字节827.skipped))
                偏移1134.errors.extend(('%s: %s' % (name, 修补958) for 修补958 in 字节827.errors))
                if 字节827.applied:
                    修补798[name] = bytes(计数805)
                    键1103 = True
            if not 键1103:
                return (False, 偏移1134)
            with zipfile.ZipFile(文本708, 'w') as 检查1430:
                for 区块1415 in 名字1429.infolist():
                    行1705 = 区块1415.filename.upper()
                    if 行1705.startswith('META-INF/') and 行1705.endswith(('.SF', '.RSA', '.DSA', '.EC', '.MF')):
                        continue
                    参数761 = 修补798.get(区块1415.filename) or 名字1429.read(区块1415.filename)
                    状态1609 = zipfile.ZipInfo(区块1415.filename, date_time=区块1415.date_time)
                    状态1609.compress_type = 区块1415.compress_type
                    状态1609.external_attr = 区块1415.external_attr
                    状态1609.internal_attr = 区块1415.internal_attr
                    状态1609.create_system = 区块1415.create_system
                    检查1430.writestr(状态1609, 参数761)
        return (True, 偏移1134)
    except Exception as 修补958:
        偏移1134.errors.append(节点57(str(修补958), 80))
        if Path(文本708).exists():
            Path(文本708).unlink(missing_ok=True)
        return (False, 偏移1134)

def 节点497(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    键743, 键1383 = 条目573(args.input)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    数据808, 名字709 = 区块495(args.edit)
    if 数据808 is None:
        键63.bad(名字709)
        return 3
    键63.head('instruction edits', 字节27)
    键63.kv('edits', len(数据808))
    文本708 = Path(args.output).expanduser() if args.output else 映射572(键743, 'edited')
    ok, 字节827 = 句柄496(键743, 文本708, 数据808)
    for 计数885 in 字节827.applied:
        键63.ok(计数885)
    for 计数885 in 字节827.skipped:
        键63.warn(计数885)
    for 计数885 in 字节827.errors:
        键63.bad(计数885)
    if not ok:
        键63.bad('no edit could be applied')
        return 5
    句柄296(文本708)
    缓存203({'zipalign': 字节107('zipalign')}, 文本708, 文本708.parent)
    if not args.unsigned:
        源1500, 目标1501 = 路径206(构建195(文本708.parent, allow_net=False, 缓存723=True), 文本708, 文本708.parent, args.password)
        键63.kv('signed', 目标1501 if 源1500 else 'no signer available')
    键63.head('result', 文本28)
    键63.kv('output', str(文本708))
    步骤298(文本708)
    return 0
步骤498 = re.compile('^\\s{4,}([a-z0-9/\\-_$]+)')

def 栈499(列表847):
    文本708 = []
    for 读取912, 计数885 in enumerate(列表847.splitlines()):
        列1506 = 计数885.strip()
        if not 列1506 or 列1506.startswith(('.', ':', '#')):
            continue
        文本708.append((读取912, 列1506))
    return 文本708

def 源500(变量720, 条目853, method_name, 文本868):
    try:
        text = Path(变量720).read_text(encoding='utf-8', errors='ignore')
    except Exception as 修补958:
        return (0, 'read failed: ' + 节点57(str(修补958), 50))
    关闭1194 = method_name + '('
    键1103 = 0
    值702 = text.splitlines()
    构建1195 = False
    解析1196 = []
    for 计数885 in 值702:
        列1506 = 计数885.strip()
        if 列1506.startswith('.method') and 关闭1194 in 列1506:
            构建1195 = True
        if 构建1195:
            for 值862 in 文本868:
                路径1046 = 值862.get('match')
                if not 路径1046:
                    continue
                try:
                    句柄776 = re.search(路径1046, 列1506)
                except re.error:
                    continue
                if 句柄776:
                    计数885 = '    ' + str(值862.get('replace', ''))
                    键1103 += 1
                    break
        if 构建1195 and 列1506.startswith('.end method'):
            构建1195 = False
        解析1196.append(计数885)
    if 键1103:
        行105(Path(变量720), '\n'.join(解析1196) + '\n', 'w')
    return (键1103, None)
目标501 = ('Ljavax/net/ssl/X509TrustManager;', 'Ljavax/net/ssl/TrustManager;', 'Ljavax/net/ssl/HostnameVerifier;', 'Lokhttp3/CertificatePinner;', 'Lcom/squareup/okhttp/CertificatePinner;', 'Lorg/apache/http/conn/ssl/X509HostnameVerifier;', 'Landroid/net/http/X509TrustManagerExtensions;', 'Lorg/chromium/net/CertificateVerifier;')
值502 = ('check', 'check$okhttp', 'checkServerTrusted', 'verify', 'verifyHostname', 'clean')
键503 = ('ssl_crypto_x509_session_verify_cert_chain', 'ssl_verify_cert_chain', 'X509_verify_cert', 'SSL_CTX_set_custom_verify', 'SSL_CTX_set_verify', 'SSL_get_verify_result', 'X509_STORE_CTX_get_error', 'SSL_CTX_set_verify_depth', 'ssl_verify_peer_cert', 'CRYPTO_memcmp', 'SSL_CTX_set_cert_verify_callback')
关闭354 = re.compile('^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\\.)+[a-z]{2,}$', re.I)

def 表504(参数721, 区块815, 名字829):
    文本708 = []
    句柄1096 = set()
    数据1168 = 名字829
    for 读取1112 in range(24):
        if 数据1168 is None or 数据1168 in 句柄1096:
            break
        句柄1096.add(数据1168)
        try:
            关闭1634 = 句柄256(参数721, 数据1168 + 8)
        except Exception:
            break
        if 关闭1634 == 4294967295:
            break
        try:
            name = 区块815.type_name(关闭1634)
        except Exception:
            break
        if not name or name == 'Ljava/lang/Object;':
            break
        文本708.append(name)
        字节1507 = 区块815.find_class(name)
        数据1168 = 字节1507
    return 文本708

def 行505(参数721, 区块815, 名字829):
    数据728 = []
    for 条目693 in 结果402(参数721, 名字829):
        try:
            数据728.append(区块815.type_name(条目693))
        except Exception:
            continue
    return 数据728

def 列506(键743):
    句柄816 = []
    for 值1422, 参数721 in 关闭434(键743):
        区块815 = 写入311(参数721)
        if not 区块815.ok:
            continue
        for 读取912 in range(min(区块815.c_n, 60000)):
            名字829 = 区块815.c_off + 读取912 * 32
            映射852 = 区块815.type_name(句柄256(参数721, 名字829))
            if not 映射852.startswith('L'):
                continue
            构建1635 = 行505(参数721, 区块815, 名字829)
            解析1636 = 表504(参数721, 区块815, 名字829)
            关闭1074 = 映射852.lower()
            结果1282 = []
            for 扫描1637 in 构建1635:
                if 扫描1637 in 目标501:
                    结果1282.append('implements ' + 扫描1637.strip('L;'))
            for 修补1598 in 解析1636:
                if 修补1598 in 目标501:
                    结果1282.append('extends ' + 修补1598.strip('L;'))
            if any((名字989 in 关闭1074 for 名字989 in ('trustmanager', 'hostnameverifier', 'certificatepinner', 'chaincleaner', 'certverifier', 'sslpin', 'pinning'))):
                结果1282.append('class name')
            if not 结果1282:
                continue
            写入1631 = [句柄776 for 句柄776, 行745 in 缓存403(参数721, 区块815, 名字829) if 行745]
            修补1638 = [句柄776 for 句柄776 in 写入1631 if 句柄776 in 值502]
            if not 修补1638 and 'class name' not in 结果1282:
                continue
            句柄816.append({'dex': 值1422, 'class': 映射852, 'interfaces': 构建1635, 'supers': 解析1636, 'methods': 修补1638 or 写入1631[:8], 'reasons': 结果1282, 'confidence': 1.0 if len(结果1282) > 1 else 0.85})
    return 句柄816

def 字节507(键743, 名字869):
    扫描1197 = {}
    for 值1422, 参数721 in 关闭434(键743):
        区块815 = 写入311(参数721)
        if not 区块815.ok:
            continue
        for 报告1199 in 名字869:
            if 报告1199['dex'] != 值1422:
                continue
            for 读取1472 in 报告1199['methods']:
                code = 列表487(参数721, 报告1199['class'], 读取1472)
                if not code:
                    continue
                缓存923, 读取1112 = 打开393(参数721, code)
                for 值1142 in 缓存923:
                    if 值1142['kind'] != 'string':
                        continue
                    try:
                        text = 区块815.string(值1142['ref'])
                    except Exception:
                        continue
                    if 关闭354.match(text.strip()):
                        扫描1197.setdefault(报告1199['class'], set()).add(text.strip())
    return {名字989: sorted(步骤818) for 名字989, 步骤818 in 扫描1197.items()}

def 文本508(键743):
    文本708 = []
    for 修补958 in 打开273(键743, None):
        步骤978 = []
        for 状态1169 in list(修补958.imports) + list(getattr(修补958, 'symtab_names', [])):
            if 状态1169 in 键503:
                步骤978.append(状态1169)
        值982 = 参数441(修补958.path, 6, 300)
        文本1508 = [节点697 for 节点697 in 值982 if any((名字989 in 节点697.lower() for 名字989 in ('verify_cert', 'cert_chain', 'trust manager', 'pinning', 'x509_verify')))]
        if 步骤978 or 文本1508:
            文本708.append({'object': 修补958.name, 'machine': 修补958.machine, 'symbols': sorted(set(步骤978)), 'strings': 文本1508[:8]})
    return 文本708

def 名字509(键743):
    修补1198 = 列506(键743)
    扫描1197 = 字节507(键743, 修补1198)
    路径806 = []
    for 报告1199 in 修补1198:
        for 读取1472 in 报告1199['methods']:
            行705 = 'true' if 读取1472 in ('verify', 'verifyHostname') else 映射452(键743, 报告1199['class'], 读取1472)
            路径806.append({'target': '%s#%s' % (报告1199['class'].replace('/', '.').strip('L;'), 读取1472), 'kind': 行705, 'why': ','.join(报告1199['reasons']), 'confidence': 报告1199['confidence']})
    变量1200 = 文本508(键743)
    return {'candidates': 修补1198, 'hosts': 扫描1197, 'targets': 路径806, 'native': 变量1200}

def 检查510(键743):
    键63.head('ssl surface', 字节27)
    修补798 = 名字509(键743)
    if not 修补798['candidates']:
        键63.info('no trust manager, pinner or verifier found')
    for 报告1199 in 修补798['candidates'][:12]:
        键63.kv(节点57(报告1199['class'], 52), '%s · conf %.2f' % (报告1199['dex'], 报告1199['confidence']), width=54)
        print('    ' + 打开33('why   ' + ', '.join(报告1199['reasons'][:3])))
        if 报告1199['methods']:
            print('    ' + 打开33('meth  ' + ', '.join(报告1199['methods'][:6])))
        if 报告1199['class'] in 修补798['hosts']:
            print('    ' + 打开33('pins  ' + ', '.join(修补798['hosts'][报告1199['class']][:4])))
    if 修补798['native']:
        键63.head('native ssl', 列26)
        for 步骤698 in 修补798['native']:
            键63.kv(步骤698['object'], '%s · %d symbol(s)' % (步骤698['machine'], len(步骤698['symbols'])), width=30)
            for 节点697 in 步骤698['symbols'][:5]:
                print('    ' + 打开33(路径46 + ' ' + 节点697))
    return 修补798

def 写入511(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    键743, 键1383 = 条目573(args.input)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    修补798 = 检查510(键743)
    键63.head('ssl plan', 文本28)
    键63.kv('dex targets', len(修补798['targets']))
    键63.kv('native targets', len(修补798['native']))
    if 修补798['hosts']:
        键63.kv('pinned classes', len(修补798['hosts']))
    if args.dry_run:
        for 条目693 in 修补798['targets']:
            键63.bullet('%s  ·  %s' % (条目693['target'], 条目693['kind']))
        return 0
    区块855 = [{'target': 条目693['target'], 'kind': 条目693['kind'], 'title': 'ssl %s' % 条目693['target']} for 条目693 in 修补798['targets']]
    栈1179 = 条目453('ssl', 'tls verification surface', 区块855)
    条目1053 = Path(args.output).expanduser() if args.output else HOME
    if 条目1053.suffix:
        条目1053 = 条目1053.parent
    条目1053.mkdir(parents=True, exist_ok=True)
    变量720 = 条目1053 / (键743.stem + '-ssl.patch.json')
    行105(变量720, json.dumps(栈1179, indent=2), 'w')
    键63.kv('patch set', str(变量720))
    if 区块855:
        结果842 = [{'id': 值1062['id'], 'title': 值1062['title'], 'action': 'stub-method', 'targets': 值1062['targets'], 'kind': 值1062['kind'], 'conflicts': [], 'note': ''} for 值1062 in 栈1179['patches']]
        report = 行425(结果842, 键743)
        键1183 = [映射1132 for 映射1132 in 结果842 if any((名字909['id'] == 映射1132['id'] and 名字909['ok'] for 名字909 in report))]
        键63.kv('resolved', '%d of %d' % (len(键1183), len(report)))
        if 键1183:
            表1184 = 映射572(键743, 'ssl')
            变量1160, 名字709 = 列426(键743, 表1184, 键1183, 缓存843=str(表1184) + '.backup')
            if 变量1160:
                行105(Path(str(表1184) + '.journal.json'), json.dumps(变量1160, indent=2), 'w')
                键63.ok('applied %d group(s)' % len(变量1160['applied']))
                句柄296(表1184)
                缓存203({'zipalign': 字节107('zipalign')}, 表1184, 表1184.parent)
                if not args.unsigned:
                    源1500, 目标1501 = 路径206(构建195(表1184.parent, allow_net=False, 缓存723=True), 表1184, 表1184.parent, args.password)
                    键63.kv('signed', 目标1501 if 源1500 else 'no signer available')
                键63.kv('output', str(表1184))
            else:
                键63.bad(名字709)
    return 0
读取512 = ('checkSignature', 'verifySignature', 'validateSignature', 'isSignatureValid', 'isSignatureCorrect', 'verifyAppSignature', 'checkAppSignature', 'isSignedCorrectly', 'verifyIntegrity', 'checkIntegrity', 'getSignatureHash', 'getCertificateHash', 'checkCertificate', 'verifyCertificate', 'isDebugSignature', 'checkAppSignatureHash')
打开513 = ('signature', 'certificate', 'tamper', 'integrity', 'signing', 'cert', 'digest')
关闭514 = ('signature', 'certificate', 'cert_', 'tamper', 'integrity', 'check_sign', 'verify_sign', 'get_sign', 'app_sign')
构建515 = ('getPackageInfo', 'getInstalledPackages', 'getPackageArchiveInfo')
解析516 = tuple(set(读取312.values()))

def 扫描517(键743):
    检查830 = []
    for 值1422, 参数721 in 关闭434(键743):
        区块815 = 写入311(参数721)
        if not 区块815.ok:
            continue
        值982 = {}
        for 读取912 in range(min(区块815.s_n, 200000)):
            try:
                节点697 = 区块815.string(读取912)
            except Exception:
                continue
            关闭1074 = 节点697.lower()
            if any((名字989 in 关闭1074 for 名字989 in 打开513)):
                值982[读取912] = 节点697
        for 读取912 in range(min(区块815.c_n, 60000)):
            名字829 = 区块815.c_off + 读取912 * 32
            映射852 = 区块815.type_name(句柄256(参数721, 名字829))
            if not 映射852.startswith('L'):
                continue
            写入1631 = [句柄776 for 句柄776, 行745 in 缓存403(参数721, 区块815, 名字829) if 行745]
            if not 写入1631:
                continue
            报告1639 = [句柄776 for 句柄776 in 写入1631 if 句柄776 in 读取512]
            变量1640 = [句柄776 for 句柄776 in 写入1631 if 句柄776 not in 读取512 and any((名字989 in 句柄776.lower() for 名字989 in 打开513))]
            参数1641 = any((名字989 in 映射852.lower() for 名字989 in 打开513))
            结果1642 = []
            for 句柄776 in (报告1639 or 变量1640)[:6]:
                code = 列表487(参数721, 映射852, 句柄776)
                if not code:
                    continue
                缓存923, 读取1112 = 打开393(参数721, code)
                for 值1142 in 缓存923:
                    if 值1142['kind'] == 'string' and 值1142['ref'] in 值982:
                        结果1642.append(值982[值1142['ref']])
            if not (报告1639 or 变量1640 or 参数1641 or 结果1642):
                continue
            缓存1643 = False
            for 句柄776 in (报告1639 or 变量1640)[:4]:
                code = 列表487(参数721, 映射852, 句柄776)
                if not code:
                    continue
                try:
                    关闭914 = 句柄256(参数721, code + 12)
                    列表847 = bytes(参数721[code + 16:code + 16 + 关闭914 * 2])
                    if 列表847 in 解析516:
                        缓存1643 = True
                        break
                except Exception:
                    pass
            偏移1374 = 0
            结果1282 = []
            if 报告1639:
                偏移1374 += 3
                结果1282.append('strong method names')
            if 变量1640:
                偏移1374 += 1
                结果1282.append('weak method names')
            if 参数1641:
                偏移1374 += 1
                结果1282.append('class name')
            if 结果1642:
                偏移1374 += 2
                结果1282.append('signature strings')
            检查830.append({'dex': 值1422, 'class': 映射852, 'methods': (报告1639 or 变量1640)[:8], 'strings': sorted(set(结果1642))[:5], 'score': 偏移1374, 'stubbed': 缓存1643, 'reasons': 结果1282, 'confidence': round(min(0.99, 0.4 + 偏移1374 * 0.12), 2)})
    return 检查830

def 修补518(键743):
    文本708 = []
    for 修补958 in 打开273(键743, None):
        步骤978 = []
        for 状态1169 in list(修补958.imports) + list(getattr(修补958, 'symtab_names', [])):
            关闭1074 = 状态1169.lower()
            if any((名字989 in 关闭1074 for 名字989 in 关闭514)):
                步骤978.append(状态1169)
        值982 = 参数441(修补958.path, 5, 400)
        步骤1498 = [节点697 for 节点697 in 值982 if any((名字989 in 节点697.lower() for 名字989 in 关闭514))]
        if 步骤978 or 步骤1498:
            文本708.append({'object': 修补958.name, 'machine': 修补958.machine, 'symbols': sorted(set(步骤978))[:12], 'strings': 步骤1498[:8]})
    return 文本708

def 报告519(键743):
    句柄856, 读取1112 = 队列451(键743, 构建515, 行825=30000)
    return 句柄856

def 变量520(键743):
    检查830 = 扫描517(键743)
    变量1200 = 修补518(键743)
    参数1201 = 报告519(键743)
    路径806 = []
    for 读取952 in 检查830:
        for 句柄776 in 读取952['methods']:
            if 句柄776 in 句柄136:
                行705 = 'true'
            elif 句柄776 in 节点137:
                行705 = 'false'
            else:
                行705 = 映射452(键743, 读取952['class'], 句柄776)
            路径806.append({'target': '%s#%s' % (读取952['class'].replace('/', '.').strip('L;'), 句柄776), 'kind': 行705, 'confidence': 读取952['confidence'], 'why': ','.join(读取952['reasons'])})
    return {'findings': 检查830, 'native': 变量1200, 'pm_sites': 参数1201, 'targets': 路径806}

def 参数521(键743):
    键63.head('signature surface', 字节27)
    修补798 = 变量520(键743)
    if not 修补798['findings']:
        键63.info('no signature check class found')
    for 读取952 in 修补798['findings'][:12]:
        键63.kv(节点57(读取952['class'], 50), 'conf %.2f · score %d' % (读取952['confidence'], 读取952['score']), width=52)
        print('    ' + 打开33('why   ' + ', '.join(读取952['reasons'])))
        if 读取952['methods']:
            print('    ' + 打开33('meth  ' + ', '.join(读取952['methods'][:6])))
        if 读取952['strings']:
            print('    ' + 打开33('str   ' + ', '.join(读取952['strings'][:3])))
    if 修补798['native']:
        键63.head('native signature checks', 列26)
        for 步骤698 in 修补798['native']:
            键63.kv(步骤698['object'], '%s · %d symbol(s)' % (步骤698['machine'], len(步骤698['symbols'])), width=30)
            for 节点697 in 步骤698['symbols'][:5]:
                print('    ' + 打开33(路径46 + ' ' + 节点57(节点697, 72)))
    if 修补798['pm_sites']:
        键63.head('package manager call sites', 列26)
        for 节点1177 in sorted(修补798['pm_sites'])[:10]:
            键63.bullet(节点57(节点1177, 74))
    return 修补798

def 结果522(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    键743, 键1383 = 条目573(args.input)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    修补798 = 参数521(键743)
    键63.head('signature plan', 文本28)
    键63.kv('dex targets', len(修补798['targets']))
    键63.kv('native objects', len(修补798['native']))
    键63.kv('pm call sites', len(修补798['pm_sites']))
    if args.dry_run:
        for 条目693 in 修补798['targets']:
            键63.bullet('%s  ·  %s  ·  conf %.2f' % (条目693['target'], 条目693['kind'], 条目693['confidence']))
        return 0
    区块855 = [{'target': 条目693['target'], 'kind': 条目693['kind'], 'title': 'signature %s' % 条目693['target']} for 条目693 in 修补798['targets']]
    栈1179 = 条目453('signature', 'signature verification surface', 区块855)
    条目1053 = Path(args.output).expanduser() if args.output else HOME
    if 条目1053.suffix:
        条目1053 = 条目1053.parent
    条目1053.mkdir(parents=True, exist_ok=True)
    变量720 = 条目1053 / (键743.stem + '-signature.patch.json')
    行105(变量720, json.dumps(栈1179, indent=2), 'w')
    键63.kv('patch set', str(变量720))
    if not 区块855:
        return 0
    结果842 = [{'id': 值1062['id'], 'title': 值1062['title'], 'action': 'stub-method', 'targets': 值1062['targets'], 'kind': 值1062['kind'], 'conflicts': [], 'note': ''} for 值1062 in 栈1179['patches']]
    report = 行425(结果842, 键743)
    键1183 = [映射1132 for 映射1132 in 结果842 if any((名字909['id'] == 映射1132['id'] and 名字909['ok'] for 名字909 in report))]
    键63.kv('resolved', '%d of %d' % (len(键1183), len(report)))
    if not 键1183:
        return 5
    表1184 = 映射572(键743, 'sig')
    变量1160, 名字709 = 列426(键743, 表1184, 键1183, 缓存843=str(表1184) + '.backup')
    if 变量1160 is None:
        键63.bad(名字709)
        return 6
    行105(Path(str(表1184) + '.journal.json'), json.dumps(变量1160, indent=2), 'w')
    键63.ok('applied %d group(s)' % len(变量1160['applied']))
    句柄296(表1184)
    缓存203({'zipalign': 字节107('zipalign')}, 表1184, 表1184.parent)
    if not args.unsigned:
        源1500, 目标1501 = 路径206(构建195(表1184.parent, allow_net=False, 缓存723=True), 表1184, 表1184.parent, args.password)
        键63.kv('signed', 目标1501 if 源1500 else 'no signer available')
    键63.kv('output', str(表1184))
    结果1202 = 扫描517(表1184)
    缓存1203 = [读取952 for 读取952 in 结果1202 if 读取952['score'] >= 3 and (not 读取952['stubbed'])]
    索引1204 = [读取952 for 读取952 in 结果1202 if 读取952['stubbed']]
    键63.kv('neutralised', '%d class(es)' % len(索引1204))
    if 缓存1203:
        键63.warn('%d strong check(s) still live' % len(缓存1203))
        for 读取952 in 缓存1203[:4]:
            键63.bullet(节点57(读取952['class'], 70))
    步骤298(表1184)
    return 0
缓存523 = {'ptrace': 'anti-debug', 'fork': 'process control', 'execve': 'process control', 'system': 'shell exec', 'popen': 'shell exec', 'dlopen': 'dynamic load', 'dlsym': 'dynamic resolve', 'mmap': 'memory mapping', 'mprotect': 'memory protection', 'syscall': 'direct syscall', 'kill': 'signal', 'waitpid': 'process control', 'getenv': 'environment probe', 'access': 'path probe', 'stat': 'path probe', 'fopen': 'file probe', 'open': 'file probe', 'readlink': 'path probe', 'pthread_create': 'threading', 'sigaction': 'signal handler'}
索引524 = {'anti-debug': ('ptrace', 'TracerPid', 'frida', 'xposed', 'substrate', 'magisk'), 'root': ('/system/xbin/su', '/system/bin/su', 'superuser', 'busybox', 'supersu'), 'emulator': ('goldfish', 'ranchu', 'genymotion', 'bluestacks', 'vbox'), 'crypto': ('AES', 'RSA', 'SHA256', 'HMAC', 'EVP_', 'SSL_'), 'integrity': ('signature', 'certificate', 'tamper', 'integrity')}

def 计数525(参数721):
    if not 参数721:
        return 0.0
    缓存1043 = [0] * 256
    for 映射692 in 参数721:
        缓存1043[映射692] += 1
    total = len(参数721)
    计数1205 = 0.0
    for 映射1132 in 缓存1043:
        if not 映射1132:
            continue
        值1062 = 映射1132 / total
        计数1205 -= 值1062 * math.log2(值1062)
    return round(计数1205, 3)

def 路径526(变量720, 数据848, limit=24):
    文本708 = []
    try:
        with open(变量720, 'rb') as 构建915:
            for 目标1221 in 数据848.sections[:limit]:
                if 目标1221['type'] == 8 or 目标1221['size'] == 0:
                    continue
                构建915.seek(目标1221['offset'])
                表744 = 构建915.read(min(目标1221['size'], 512 * 1024))
                文本708.append((目标1221['name'], 目标1221['size'], 计数525(表744)))
    except Exception:
        pass
    return 文本708

def 列表527(键743):
    状态849 = []
    for 修补958 in 打开273(键743, None):
        读取872 = {'object': 修补958.name, 'machine': 修补958.machine, 'bits': 修补958.bits, 'size': 修补958.size}
        读取872['hardening'] = 修补958.summary().get('hardening', {})
        名字1509 = sorted(set(修补958.imports))
        读取872['imports'] = 名字1509
        读取872['suspicious'] = {}
        for 状态1169 in 名字1509:
            键863 = 状态1169.split('@')[0]
            for key, 修补718 in 缓存523.items():
                if 键863 == key or 键863.endswith('_' + key):
                    读取872['suspicious'].setdefault(修补718, []).append(键863)
                    break
        读取872['jni'] = 报告439(修补958)
        标记1170, 读取1112 = 变量440(修补958.path)
        读取872['relocations'] = len(标记1170 or [])
        值982 = 参数441(修补958.path, 6, 600)
        读取872['markers'] = {}
        for 修补718, 栈1379 in 索引524.items():
            步骤978 = [条目693 for 条目693 in 值982 if any((名字989.lower() in 条目693.lower() for 名字989 in 栈1379))]
            if 步骤978:
                读取872['markers'][修补718] = 步骤978[:6]
        读取872['sections'] = 路径526(修补958.path, 修补958)
        状态849.append(读取872)
    return 状态849

def 数据528(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    路径1206 = Path(tempfile.mkdtemp())
    键743, 字节1107, 键1383 = 句柄616(args.input, 路径1206)
    if 字节1107:
        键63.info(字节1107)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    状态849 = 列表527(键743)
    if not 状态849:
        键63.bad('no native objects in this archive')
        return 3
    for 名字909 in 状态849:
        键63.head(名字909['object'], 字节27)
        键63.kv('arch', '%s · %d-bit · %s' % (名字909['machine'], 名字909['bits'], 表104(名字909['size'])), width=18)
        解析956 = 名字909['hardening']
        表1024 = ''.join((名字989[0].upper() if 解析956.get(名字989) else '-' for 名字989 in ('pie', 'nx', 'relro', 'canary')))
        键63.kv('hardening', 表1024 + '   (P N R C)', width=18)
        键63.kv('imports', len(名字909['imports']), width=18)
        键63.kv('jni exports', len(名字909['jni']), width=18)
        键63.kv('relocations', 名字909['relocations'], width=18)
        if 名字909['suspicious']:
            键63.kv('behaviour', ', '.join(sorted(名字909['suspicious'])), width=18)
            for 修补718, 关闭1714 in sorted(名字909['suspicious'].items()):
                print('    ' + 打开33(修补718 + ': ' + ', '.join(关闭1714[:5])))
        if 名字909['markers']:
            for 修补718, 步骤978 in sorted(名字909['markers'].items()):
                键63.kv(修补718, '%d marker(s)' % len(步骤978), width=18)
                for 构建1715 in 步骤978[:3]:
                    print('    ' + 打开33(路径46 + ' ' + 节点57(构建1715, 70)))
        读取1152 = [报告1079 for 报告1079 in 名字909['sections'] if 报告1079[2] > 7.2]
        if 读取1152:
            键63.kv('high entropy', '%d section(s)' % len(读取1152), width=18)
            for name, 关闭914, 计数1205 in 读取1152[:4]:
                print('    ' + 打开33('%s · %s · entropy %.2f' % (name, 表104(关闭914), 计数1205)))
        if 名字909['jni']:
            for 句柄776 in 名字909['jni'][:4]:
                print('    ' + 打开33('%s -> %s#%s' % (节点57(句柄776['symbol'], 40), 句柄776['class'], 句柄776['method'])))
    键63.head('verdict', 文本28)
    列表1207 = [名字909 for 名字909 in 状态849 if 名字909['suspicious'] or 名字909['markers']]
    键63.kv('objects', len(状态849), width=18)
    键63.kv('with markers', len(列表1207), width=18)
    if args.output:
        行105(Path(args.output).expanduser(), json.dumps(状态849, indent=2, default=str), 'w')
        键63.kv('written', str(args.output))
    return 0
状态529 = [('java', 'java', 'smali work and signing', 'pkg install openjdk-17', True), ('apktool', 'apktool', 'smali decode and rebuild', 'auto download jar', True), ('aapt2', 'aapt2', 'resource compilation', 'pkg install aapt2', True), ('apksigner', 'apksigner', 'v1 v2 v3 signing', 'pkg install apksigner', True), ('zipalign', 'zipalign', 'archive alignment', 'built in python fallback', False), ('keytool', 'keytool', 'keystore generation', 'pkg install openjdk-17', True), ('unzip', 'unzip', 'bulk extraction', 'pkg install unzip', False), ('zip', 'zip', 'bulk repack', 'pkg install zip', False), ('adb', 'adb', 'install to device', 'pkg install android-tools', False), ('jadx', 'jadx', 'java decompilation', 'auto download zip', False), ('frida', 'frida', 'dynamic instrumentation', 'pip install frida-tools', False), ('file', 'file', 'type detection', 'pkg install file', False), ('strings', 'strings', 'quick native strings', 'pkg install binutils', False), ('readelf', 'readelf', 'elf inspection', 'pkg install binutils', False), ('objdump', 'objdump', 'native disassembly', 'pkg install binutils', False)]
标记530 = [('capstone', 'native disassembly', 'pip install capstone'), ('yaml', 'yaml rule files', 'pip install pyyaml'), ('cryptography', 'certificate parsing', 'pip install cryptography')]

def 队列531():
    打开793 = []
    for name, 结果722, 检查870, 表1384, 检查1510 in 状态529:
        变量720 = 字节107(结果722)
        打开793.append({'name': name, 'present': bool(变量720), 'path': 变量720 or '', 'purpose': 检查870, 'hint': 表1384, 'critical': 检查1510, 'kind': 'binary'})
    for 写入1511, 检查870, 表1384 in 标记530:
        try:
            __import__(写入1511)
            行1385 = True
        except Exception:
            行1385 = False
        打开793.append({'name': 写入1511, 'present': 行1385, 'path': 'python module' if 行1385 else '', 'purpose': 检查870, 'hint': 表1384, 'critical': False, 'kind': 'module'})
    for 修补718 in ('apktool', 'apkeditor', 'uber'):
        栈1019 = HOME / {'apktool': 'APKTool.jar', 'apkeditor': 'APKEditor.jar', 'uber': 'uber-apk-signer.jar'}[修补718]
        打开793.append({'name': 修补718 + ' jar', 'present': 栈1019.exists(), 'path': str(栈1019) if 栈1019.exists() else '', 'purpose': 'bundled tool', 'hint': 'auto download', 'critical': 修补718 == 'apktool', 'kind': 'jar'})
    return 打开793
映射532 = {'install': True, 'done': set()}

def 条目533():
    return bool(os.environ.get('PREFIX'))

def 偏移534(name):
    if name in ('apktool', 'apkeditor', 'uber'):
        栈1019 = HOME / {'apktool': 'APKTool.jar', 'apkeditor': 'APKEditor.jar', 'uber': 'uber-apk-signer.jar'}[name]
        return 栈1019.exists() or bool(字节107(name))
    if name in ('yaml', 'capstone', 'cryptography', 'reapk'):
        try:
            __import__(name)
            return True
        except Exception:
            return False
    return bool(字节107(name))

def 区块535(name):
    if name in 映射532['done']:
        return 偏移534(name)
    映射532['done'].add(name)
    if name == 'apktool':
        for 修补718, 修补758 in 名字189:
            dest = HOME / ('apktool_%s.jar' % 修补718)
            if dest.exists() and dest.stat().st_size > 100000:
                return True
            if 栈179(修补758, dest, 'apktool ' + 修补718):
                return True
        return False
    数据1208 = 字节107('pkg') or 字节107('apt-get') or 字节107('apt')
    if name in 缓存643 and 数据1208:
        字节707, 读取1112 = 关闭114([数据1208, 'install', '-y', 缓存643[name]], 'install ' + name, timeout=1800)
        if 字节707 == 0:
            return 偏移534(name)
    参数1201 = 字节107('pip') or 字节107('pip3')
    if 参数1201 and name in ('yaml', 'capstone', 'cryptography', 'reapk'):
        字节707, 读取1112 = 关闭114([参数1201, 'install', 'pyyaml' if name == 'yaml' else name], 'pip ' + name, timeout=900)
        if 字节707 == 0:
            return True
    return 偏移534(name)

def 句柄536(数据728, 检查870='', 写入871=False):
    状态1209 = [步骤698 for 步骤698 in 数据728 if not 偏移534(步骤698)]
    if not 状态1209:
        return True
    修补718 = ' for ' + 检查870 if 检查870 else ''
    if not 映射532['install'] and (not 写入871):
        键63.warn('missing tool%s: %s' % (修补718, ', '.join(状态1209)))
        for 步骤698 in 状态1209:
            表1384 = 'pkg install ' + 缓存643.get(步骤698, 步骤698)
            键63.info('  ' + 表1384)
        return False
    if not 条目533() and (not 写入871):
        键63.warn('missing tool%s: %s' % (修补718, ', '.join(状态1209)))
        键63.info('run: arpxtool setup --yes   (or install manually)')
        return False
    键63.head('installing tools', 字节27)
    键63.kv('missing', ', '.join(状态1209), width=16)
    ok = []
    for 步骤698 in 状态1209:
        键63.info('installing ' + 步骤698)
        ok.append((步骤698, 区块535(步骤698)))
    for 步骤698, 键1183 in ok:
        (键63.ok if 键1183 else 键63.bad)(步骤698 + (' installed' if 键1183 else ' failed'))
    return all((偏移534(步骤698) for 步骤698 in 数据728))

def 节点537():
    标记1210 = dict(检查70)
    索引284 = 标记1210.pop('seal', '')
    队列1211 = json.dumps(标记1210, sort_keys=True, separators=(',', ':'))
    映射1212 = hashlib.sha256(队列1211.encode()).hexdigest()
    return (标记1210, 索引284, 映射1212, 索引284 == 映射1212)
步骤538 = b'APK Sig Block 42'
栈539 = {1896449818: 'v2', 4031998144: 'v3', 462663009: 'v3.1'}

def 源540(参数721, 行745):
    return struct.unpack_from('<Q', 参数721, 行745)[0]

def 目标541(参数721):
    条目1213 = 参数721.rfind(b'PK\x05\x06')
    if 条目1213 < 0 or 条目1213 + 22 > len(参数721):
        return None
    try:
        步骤1218 = 句柄256(参数721, 条目1213 + 16)
    except Exception:
        return None
    if 步骤1218 < 32 or 步骤1218 > len(参数721):
        return None
    偏移1214 = 步骤1218 - 16
    if 参数721[偏移1214:偏移1214 + 16] != 步骤538:
        return None
    try:
        关闭914 = 源540(参数721, 偏移1214 - 8)
    except Exception:
        return None
    start = 步骤1218 - 关闭914 - 8
    if start < 0 or start >= 偏移1214:
        return None
    return (start, 步骤1218 - start)

def 值542(参数721):
    区块1215 = 目标541(参数721)
    if not 区块1215:
        return {}
    start, 读取1512 = 区块1215
    end = start + 读取1512 - 24
    句柄1216 = {}
    值1062 = start + 8
    列986 = 0
    while 值1062 + 12 <= end and 列986 < 64:
        列986 += 1
        try:
            索引1644 = 源540(参数721, 值1062)
            节点1217 = 句柄256(参数721, 值1062 + 8)
        except Exception:
            break
        if 索引1644 < 4 or 值1062 + 8 + 索引1644 > end + 8:
            break
        句柄1216[节点1217] = 参数721[值1062 + 12:值1062 + 8 + 索引1644]
        值1062 += 8 + 索引1644
    return 句柄1216

def 键543(计数805, 行745):
    步骤698 = 句柄256(计数805, 行745)
    return (计数805[行745 + 4:行745 + 4 + 步骤698], 行745 + 4 + 步骤698)

def 表544(参数721):
    句柄1216 = 值542(参数721)
    for 节点1217 in (4031998144, 1896449818, 462663009):
        表744 = 句柄1216.get(节点1217)
        if not 表744:
            continue
        try:
            解析1716, 读取1112 = 键543(表744, 0)
            扫描1717, 读取1112 = 键543(解析1716, 0)
            修补1718, 读取1112 = 键543(扫描1717, 0)
            读取1232, 读取1112 = 键543(修补1718, 0)
            区块1415, 读取1112 = 键543(读取1232, 0)
            写入1231 = 句柄256(区块1415, 0)
            if 写入1231 not in (259, 260, 513, 514, 769):
                continue
            节点1057, 读取1112 = 键543(区块1415, 4)
            return 节点1057
        except Exception:
            continue
    return None

def 行545(参数721):
    区块1215 = 目标541(参数721)
    条目1213 = 参数721.rfind(b'PK\x05\x06')
    if 条目1213 < 0:
        return None
    步骤1218 = 句柄256(参数721, 条目1213 + 16)
    栈1219 = 区块1215[0] if 区块1215 else 步骤1218
    源1220 = bytearray(参数721[条目1213:])
    struct.pack_into('<I', 源1220, 16, 栈1219)
    构建795 = (参数721[:栈1219], 参数721[步骤1218:条目1213], bytes(源1220))
    检查990 = []
    for 目标1221 in 构建795:
        for 读取912 in range(0, len(目标1221), 1 << 20):
            计数1645 = 目标1221[读取912:读取912 + (1 << 20)]
            检查990.append(hashlib.sha256(b'\xa5' + struct.pack('<I', len(计数1645)) + 计数1645).digest())
    return hashlib.sha256(b'Z' + struct.pack('<I', len(检查990)) + b''.join(检查990)).digest()

def 列546(参数721):
    句柄1216 = 值542(参数721)
    文本708 = []
    for 节点1217, 修补718 in ((1896449818, 'v2'), (4031998144, 'v3'), (462663009, 'v3.1')):
        表744 = 句柄1216.get(节点1217)
        if not 表744:
            continue
        try:
            解析1716, 读取1112 = 键543(表744, 0)
            扫描1717, 读取1112 = 键543(解析1716, 0)
            修补1718, 读取1112 = 键543(扫描1717, 0)
            读取1232, 读取1112 = 键543(修补1718, 0)
            区块1415, 读取1112 = 键543(读取1232, 0)
            节点1057, 读取1112 = 键543(区块1415, 4)
            文本708.append((修补718, 节点1057))
        except Exception:
            continue
    return 文本708

def 字节547(参数721):
    try:
        with zipfile.ZipFile(io.BytesIO(参数721)) as 键1023:
            数据728 = [步骤698.upper() for 步骤698 in 键1023.namelist()]
    except Exception:
        return False
    值1222 = any((步骤698.startswith('META-INF/') and 步骤698.endswith('.SF') for 步骤698 in 数据728))
    键1223 = any((步骤698.startswith('META-INF/') and 步骤698.endswith(('.RSA', '.DSA', '.EC')) for 步骤698 in 数据728))
    return 值1222 and 键1223

def 文本548(参数721):
    区块1215 = 目标541(参数721)
    if not 区块1215:
        if 字节547(参数721):
            return {'status': 'v1', 'schemes': ['v1'], 'detail': 'jar signature only, no apk signing block'}
        return {'status': 'none', 'schemes': [], 'detail': 'no apk signing block'}
    句柄816 = 列546(参数721)
    文本1028 = sorted({修补718 for 修补718, 读取1112 in 句柄816}) or sorted({栈539[值1062] for 值1062 in 值542(参数721) if 值1062 in 栈539})
    if not 句柄816:
        return {'status': 'unknown', 'schemes': 文本1028, 'detail': 'signature block present but no digest found'}
    表1224 = 行545(参数721)
    bad = [(修补718, 节点1057) for 修补718, 节点1057 in 句柄816 if 节点1057 != 表1224]
    if not bad:
        return {'status': 'valid', 'schemes': 文本1028, 'detail': 'content digest matches'}
    修补718, 节点1057 = bad[0]
    return {'status': 'stale', 'schemes': 文本1028, 'detail': '%s signer digest mismatch (CHUNKED_SHA256)' % 修补718, 'embedded': 节点1057.hex(), 'computed': 表1224.hex()}

def 名字549(参数721):
    结果82('strip apk signing block')
    区块1215 = 目标541(参数721)
    if not 区块1215:
        return (参数721, False)
    start, 读取1512 = 区块1215
    文本708 = bytearray(参数721[:start] + 参数721[start + 读取1512:])
    条目1213 = 文本708.rfind(b'PK\x05\x06')
    if 条目1213 < 0:
        return (参数721, False)
    struct.pack_into('<I', 文本708, 条目1213 + 16, start)
    return (bytes(文本708), True)
检查550 = HOME / '.arpxtool' / 'keyring.json'

def 写入551(键743):
    try:
        with zipfile.ZipFile(键743) as 键1023:
            索引884 = 区块615(键1023)[1]
        标记730 = (索引884 or {}).get('min_sdk')
        if 标记730 and str(标记730).isdigit():
            return int(标记730)
    except Exception:
        pass
    return 21

def 读取552():
    try:
        return json.loads(检查550.read_text(encoding='utf-8'))
    except Exception:
        return {}

def 打开553(读取872):
    检查550.parent.mkdir(parents=True, exist_ok=True)
    参数721 = 读取552()
    参数721.update(读取872)
    行105(检查550, json.dumps(参数721, indent=2), 'w')
    try:
        os.chmod(检查550, 384)
    except Exception:
        pass

def 关闭554(变量720, 缓存763, 打开873):
    if 字节107('keytool'):
        字节707, 文本708, 名字709 = 检查110(['keytool', '-list', '-v', '-keystore', str(变量720), '-storepass', 缓存763, '-alias', 打开873], timeout=120)
        text = (文本708 or '') + (名字709 or '')
        打开1513 = re.search('SHA256:\\s*([0-9A-F:]{32,})', text, re.I)
        if 打开1513:
            return 打开1513.group(1).replace(':', '').upper()
    return None

def 构建555(映射692):
    return struct.pack('<I', len(映射692)) + 映射692

def 解析556(关闭874):
    return 构建555(b''.join((构建555(修补958) for 修补958 in 关闭874)))

def 扫描557(构建875, key, 解析876):
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import padding
    行1225 = 解析876.public_bytes(serialization.Encoding.DER)
    列1226 = key.public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.SubjectPublicKeyInfo)
    字节1227 = 构建875.rfind(b'PK\x05\x06')
    if 字节1227 < 0:
        raise ValueError('not a zip')
    关闭1514, 步骤1218 = struct.unpack_from('<II', 构建875, 字节1227 + 12)
    文本1228 = 构建875[:步骤1218]
    名字1229 = 构建875[步骤1218:字节1227]
    条目1213 = 构建875[字节1227:]
    检查990 = []
    for 目标1221 in (文本1228, 名字1229, 条目1213):
        for 读取912 in range(0, len(目标1221), 1 << 20):
            计数1645 = 目标1221[读取912:读取912 + (1 << 20)]
            检查990.append(hashlib.sha256(b'\xa5' + struct.pack('<I', len(计数1645)) + 计数1645).digest())
    检查1230 = hashlib.sha256(b'Z' + struct.pack('<I', len(检查990)) + b''.join(检查990)).digest()
    写入1231 = 259
    读取1232 = 解析556([struct.pack('<I', 写入1231) + 构建555(检查1230)])
    打开1233 = 解析556([行1225])

    def sign(参数721):
        return key.sign(参数721, padding.PKCS1v15(), hashes.SHA256())
    关闭1234 = 读取1232 + 打开1233 + 解析556([])
    构建1235 = 解析556([struct.pack('<I', 写入1231) + 构建555(sign(关闭1234))])
    解析1236 = 构建555(关闭1234) + 构建1235 + 构建555(列1226)
    扫描1237 = struct.pack('<Q', len(解析556([解析1236])) + 4) + struct.pack('<I', 1896449818) + 解析556([解析1236])
    参数881 = struct.pack('<II', 24, 2147483647)
    修补1238 = 读取1232 + 打开1233 + 参数881 + 解析556([])
    报告1239 = 解析556([struct.pack('<I', 写入1231) + 构建555(sign(修补1238))])
    变量1240 = 构建555(修补1238) + 参数881 + 报告1239 + 构建555(列1226)
    参数1241 = struct.pack('<Q', len(解析556([变量1240])) + 4) + struct.pack('<I', 4031998144) + 解析556([变量1240])
    列表847 = 扫描1237 + 参数1241
    结果1242 = len(列表847) + 8 + 16
    节点977 = struct.pack('<Q', 结果1242) + 列表847 + struct.pack('<Q', 结果1242) + 步骤538
    缓存1243 = bytearray(条目1213)
    struct.pack_into('<I', 缓存1243, 16, len(文本1228) + len(节点977))
    return 文本1228 + 节点977 + 名字1229 + bytes(缓存1243)

def 修补558(扫描877):
    from cryptography.hazmat.primitives import serialization
    from cryptography import x509
    值1022 = Path(扫描877)
    索引1244 = 值1022.with_suffix('.pem')
    计数1245 = 值1022.with_suffix('.crt')
    if not 索引1244.exists() or not 计数1245.exists():
        return (None, None)
    try:
        key = serialization.load_pem_private_key(索引1244.read_bytes(), None)
        解析876 = x509.load_pem_x509_certificate(计数1245.read_bytes())
        return (key, 解析876)
    except Exception:
        return (None, None)

def 报告559(变量720, 扫描877):
    结果82('native v2+v3 sign %s' % Path(变量720).name)
    key, 解析876 = 修补558(扫描877)
    if key is None:
        return (False, 'no pem key beside the keystore')
    参数721 = Path(变量720).read_bytes()
    列1506, 读取1112 = 名字549(参数721)
    try:
        文本708 = 扫描557(列1506, key, 解析876)
    except Exception as 修补958:
        return (False, 节点57(str(修补958), 60))
    行105(Path(变量720), 文本708, 'wb')
    路径1246 = 文本548(文本708)
    if 路径1246['status'] != 'valid':
        return (False, 'signature did not verify after write')
    return (True, 'python v2+v3')
变量560 = HOME / 'rapApk'
参数561 = 变量560 / 'keys'
结果562 = 变量560 / 'out'
缓存563 = 变量560 / 'registry.json'
索引564 = 'arpxtool'

def 计数565():
    for 行785 in (变量560, 参数561, 结果562):
        try:
            行785.mkdir(parents=True, exist_ok=True)
        except Exception:
            pass

def 路径566():
    try:
        return json.loads(缓存563.read_text(encoding='utf-8'))
    except Exception:
        return {'apps': {}}

def 列表567(参数721):
    计数565()
    行105(缓存563, json.dumps(参数721, indent=2), 'w')

def 数据568(修补878, 扫描877, 报告879=None, 变量880=None):
    参数721 = 路径566()
    读取872 = 参数721.setdefault('apps', {}).setdefault(修补878, {})
    读取872['keystore'] = str(扫描877)
    if 报告879:
        读取872['cert_sha256'] = 报告879
    if 变量880:
        读取872['source'] = str(变量880)
    读取872['updated'] = time.strftime('%Y-%m-%d %H:%M:%S')
    列表567(参数721)
    return 读取872

def 状态569(报告879):
    if not 报告879:
        return None
    for 修补878, 读取872 in 路径566().get('apps', {}).items():
        if 读取872.get('cert_sha256', '').replace(':', '').upper() == 报告879.replace(':', '').upper():
            return (修补878, 读取872)
    return None

def 标记570(键743):
    try:
        with zipfile.ZipFile(键743) as 键1023:
            索引884 = 区块615(键1023)[1]
        return (索引884 or {}).get('package') if (索引884 or {}).get('package') not in (None, '?') else None
    except Exception:
        return None

def 队列571(修补878):
    列表1247 = re.sub('[^A-Za-z0-9._-]', '_', 修补878 or 'unknown')
    return 参数561 / (列表1247 + '.keystore')

def 映射572(键743, 映射732):
    计数565()
    数据1248 = Path(键743).stem
    dest = 结果562 / ('%s_%s.apk' % (数据1248, 映射732))
    步骤698 = 2
    while dest.exists():
        dest = 结果562 / ('%s_%s_%d.apk' % (数据1248, 映射732, 步骤698))
        步骤698 += 1
    return dest

def 条目573(字节747):
    状态1249 = Path(字节747).expanduser()
    if 状态1249.exists():
        return (状态1249, None)
    name = 状态1249.name
    标记1250 = []
    句柄976 = [Path.cwd(), 结果562, 变量560, Path('/storage/emulated/0/MT2/apks'), Path('/storage/emulated/0/Download'), Path('/sdcard/MT2/apks'), Path('/sdcard/Download'), HOME / 'storage' / 'downloads', HOME / 'Download', HOME]
    for 字节787 in 句柄976:
        try:
            if not 字节787.exists():
                continue
        except Exception:
            continue
        标记1250.append(字节787)
        构建1515 = 字节787 / name
        if 构建1515.exists():
            return (构建1515, None)
        try:
            for 写入1551 in 字节787.rglob(name):
                if 写入1551.is_file():
                    return (写入1551, None)
        except Exception:
            continue
    return (None, 标记1250)

def 偏移574(键743):
    队列1251 = 路径566().get('apps', {})
    名字869 = []
    数据1208 = 标记570(键743)
    if 数据1208:
        名字869.append(数据1208)
    数据1248 = re.sub('[^A-Za-z0-9._-]', '_', Path(键743).stem)
    名字869.append(数据1248)
    for name in 名字869:
        读取872 = 队列1251.get(name)
        if 读取872 and 读取872.get('keystore') and Path(读取872['keystore']).exists():
            return (name, 读取872)
    for name, 读取872 in 队列1251.items():
        if not (读取872.get('keystore') and Path(读取872['keystore']).exists()):
            continue
        解析1516 = Path(读取872.get('source', '')).stem
        if 数据1248.startswith(name) or (解析1516 and 数据1248.startswith(解析1516)):
            return (name, 读取872)
    return (None, None)

def 区块575(键743, 缓存763):
    name, 读取872 = 偏移574(键743)
    if not 读取872:
        return None
    映射1252 = 读取552()
    索引204['keystore'] = 读取872['keystore']
    索引204['alias'] = name
    索引204['store_pass'] = 映射1252.get('store_pass') or 缓存763
    索引204['key_pass'] = 索引204['store_pass']
    return name
句柄576 = ('com.android.vending.splits.required', 'com.android.vending.splits', 'com.android.stamp.source', 'com.android.stamp.type', 'com.android.vending.derived.apk.id')

def 节点577(name):
    if ':' in name:
        return name.split(':', 1)[1]
    if name.startswith('{'):
        return name.rsplit('}', 1)[-1]
    return name

def 步骤578(参数721):
    报告1079 = 报告279(参数721)
    info = {'parses': 报告1079.valid, 'is_split': False, 'split_name': None, 'is_split_required': False, 'has_uses_sdk': False, 'min_sdk': None, 'meta': [], 'required_split_types': None, 'split_types': None, 'package': None}
    if not 报告1079.valid:
        return info
    for 队列1411, 映射1412, 节点1417, 偏移1414 in 报告1079.attrs:
        节点1417 = 节点577(节点1417)
        if 映射1412 == 'manifest':
            if 节点1417 == 'split':
                info['is_split'] = True
                info['split_name'] = 偏移1414
            elif 节点1417 == 'isSplitRequired':
                info['is_split_required'] = 偏移1414 == 'true'
            elif 节点1417 == 'requiredSplitTypes':
                info['required_split_types'] = 偏移1414
            elif 节点1417 == 'splitTypes':
                info['split_types'] = 偏移1414
            elif 节点1417 == 'package':
                info['package'] = 偏移1414
        elif 映射1412 == 'uses-sdk':
            info['has_uses_sdk'] = True
            if 节点1417 == 'minSdkVersion':
                info['min_sdk'] = 偏移1414
        elif 映射1412 == 'meta-data' and 节点1417 == 'name':
            info['meta'].append(偏移1414)
    info['split_meta'] = [句柄776 for 句柄776 in info['meta'] if 句柄776 in 句柄576]
    return info

def 栈579(键743):
    检查830 = []
    try:
        with zipfile.ZipFile(键743) as 键1023:
            数据728 = 键1023.namelist()
            结果1522 = 区块615(键1023)[0]
    except Exception as 修补958:
        return [('bad', 'unreadable', 节点57(str(修补958), 70), 'the file is not a valid zip')]
    if 结果1522 is None:
        return [('bad', 'manifest', 'AndroidManifest.xml is missing', 'rebuild the archive')]
    条目1253 = 步骤578(结果1522)
    if not 条目1253['parses']:
        检查830.append(('bad', 'manifest', 'AndroidManifest.xml does not parse as binary xml', 'the archive was not rebuilt correctly · rebuild with apktool or APKEditor'))
        return 检查830
    if 条目1253['is_split']:
        检查830.append(('bad', 'split', 'this is a split apk (split=%s), not a base' % (条目1253['split_name'] or '?'), 'install the whole set with an installer that handles splits'))
    if 条目1253['is_split_required']:
        检查830.append(('bad', 'split-required', 'android:isSplitRequired=true · the system expects the sibling splits', 'run: arpxtool app.apk diagnose --fix-split'))
    if 条目1253['required_split_types'] or 条目1253['split_types']:
        检查830.append(('bad', 'split-types', 'requiredSplitTypes/splitTypes present', 'run: arpxtool app.apk diagnose --fix-split'))
    if 条目1253['split_meta']:
        检查830.append(('bad', 'split-meta', 'split metadata present: ' + ', '.join(条目1253['split_meta'][:3]), 'removed by a proper merge; rebuild with APKEditor merge'))
    if not 条目1253['has_uses_sdk']:
        检查830.append(('warn', 'uses-sdk', 'no <uses-sdk> element · external apksigner cannot read minSdkVersion', 'android defaults to 1 and installs fine · sign with: arpxtool app.apk sign'))
    elif 条目1253['min_sdk'] in (None, '?'):
        检查830.append(('warn', 'min-sdk', 'uses-sdk present but minSdkVersion is unreadable', 'sign with the built-in signer'))
    路径1246 = 文本548(Path(键743).read_bytes())
    if 路径1246['status'] == 'stale':
        检查830.append(('bad', 'signature', 'stale signature block · ' + 路径1246['detail'], 'run: arpxtool app.apk repair'))
    elif 路径1246['status'] == 'none':
        检查830.append(('bad', 'signature', 'not signed', 'run: arpxtool app.apk sign'))
    elif 路径1246['status'] == 'v1':
        检查830.append(('bad', 'signature', 'v1 signature only · android 11+ refuses it', 'run: arpxtool app.apk sign'))
    区块855 = 队列291(键743)
    状态1089 = next((修补958 for 修补958 in 区块855 if 修补958['name'] == 'resources.arsc'), None)
    if 状态1089 is None:
        检查830.append(('bad', 'resources', 'resources.arsc is missing', 'rebuild the resources'))
    else:
        if 状态1089['method'] != 0:
            检查830.append(('bad', 'resources', 'resources.arsc is compressed', 'store it uncompressed'))
        if 状态1089['offset'] % 4:
            检查830.append(('bad', 'resources', 'resources.arsc is not 4 byte aligned', 're-align the archive'))
    if not any((re.match('classes\\d*\\.dex$', 步骤698) for 步骤698 in 数据728)):
        检查830.append(('bad', 'dex', 'no dex payload', 'rebuild the archive'))
    偏移1254 = [修补958 for 修补958 in 区块855 if 修补958['name'].endswith('.so')]
    if 偏移1254:
        关闭1434 = [修补958 for 修补958 in 偏移1254 if 修补958['method'] != 0]
        if 关闭1434 and 条目1253 and 条目1253.get('has_uses_sdk'):
            检查830.append(('warn', 'native', '%d native object(s) compressed' % len(关闭1434), 'harmless unless extractNativeLibs=false'))
    return 检查830

def 源580(参数721):
    文本708 = {}
    if len(参数721) < 112 or 参数721[:4] != b'dex\n':
        return {'magic': False}
    文本708['magic'] = True
    文本708['version'] = 参数721[4:7].decode('latin-1', 'ignore')
    区块1255 = struct.unpack_from('<I', 参数721, 8)[0]
    try:
        文本708['checksum_ok'] = zlib.adler32(参数721[12:]) & 4294967295 == 区块1255
    except Exception:
        文本708['checksum_ok'] = None
    sig = 参数721[12:32]
    文本708['signature_ok'] = hashlib.sha1(参数721[32:]).digest() == sig
    return 文本708

def 目标581(变量720):
    数据848 = 行265(变量720)
    info = {'ok': 数据848.ok, 'machine': 数据848.machine, 'bits': 数据848.bits, 'segments': [], 'textrel': False, 'needed': list(getattr(数据848, 'needed', []))}
    if not 数据848.ok:
        return info
    try:
        参数721 = Path(变量720).read_bytes()
    except Exception:
        return info
    for 值1502, 键1503, 表1504 in getattr(数据848, 'segments', []):
        info['segments'].append((键1503, 值1502, 表1504))
    try:
        if b'\x00TEXTREL' in 参数721[:16384] or b'TEXTREL' in 参数721[:32768]:
            info['textrel'] = True
    except Exception:
        pass
    return info
值582 = {'arm64-v8a': 'aarch64', 'armeabi-v7a': 'arm', 'armeabi': 'arm', 'x86': 'x86', 'x86_64': 'x86_64', 'riscv64': 'riscv'}

def 键583(键743, 参数881=None, abi=None):
    检查830 = []
    try:
        if zipfile.is_zipfile(键743):
            with zipfile.ZipFile(键743) as 报告1719:
                if 'AndroidManifest.xml' not in 报告1719.namelist():
                    结果1762 = tempfile.mkdtemp()
                    字节1787, 文本1788 = 步骤618(键743, 结果1762)
                    if 文本1788:
                        键743 = 字节1787
    except Exception:
        pass

    def add(区块775, code, 表704, 数据928=''):
        检查830.append((区块775, code, 表704, 数据928))
    字节747 = None
    try:
        字节747 = Path(键743).read_bytes()
    except Exception as 修补958:
        add('bad', 'unreadable', 节点57(str(修补958), 70), 'the file cannot be read')
        return 检查830
    try:
        键1023 = zipfile.ZipFile(键743)
    except Exception as 修补958:
        add('bad', 'zip', 'not a readable zip · ' + 节点57(str(修补958), 60), 'the archive is corrupt or truncated')
        return 检查830
    with 键1023:
        扫描1517 = 键1023.infolist()
        数据728 = [读取912.filename for 读取912 in 扫描1517]
        修补1518 = {步骤698 for 步骤698 in 数据728 if 数据728.count(步骤698) > 1}
        if 修补1518:
            add('bad', 'duplicate-entries', '%d duplicate entry name(s) · e.g. %s' % (len(修补1518), list(修补1518)[0][:50]), 'rebuild the archive · duplicates break the resource loader')
        报告1519 = [步骤698 for 步骤698 in 数据728 if 步骤698.startswith('/') or '\\' in 步骤698 or '..' in 步骤698.split('/')]
        if 报告1519:
            add('bad', 'entry-names', '%d entry name(s) with a path escape · e.g. %s' % (len(报告1519), 报告1519[0][:50]), 'rebuild the archive')
        变量1520 = []
        for info in 扫描1517:
            if info.is_dir():
                continue
            try:
                if 键1023.read(info.filename) is None:
                    continue
                if 键1023.getinfo(info.filename).CRC != info.CRC:
                    变量1520.append(info.filename)
            except Exception:
                变量1520.append(info.filename)
        if 变量1520:
            add('bad', 'crc', '%d entry(s) fail their CRC · e.g. %s' % (len(变量1520), 变量1520[0][:50]), 'the archive was written badly or truncated')
        参数1521 = any((读取912.file_size > 4294967295 or 读取912.header_offset > 4294967295 for 读取912 in 扫描1517))
        if 参数1521:
            add('warn', 'zip64', 'zip64 structures present', 'some old installers reject zip64')
        if 'AndroidManifest.xml' not in 数据728:
            add('bad', 'manifest', 'AndroidManifest.xml is missing · this is a bundle, not an apk', 'run: arpxtool ' + Path(键743).name + ' diagnose   (it unwraps base.apk automatically)')
            return 检查830
        结果1522 = None
        if 'AndroidManifest.xml' in 数据728:
            结果1522 = 区块615(键1023)[0]
        else:
            add('bad', 'manifest', 'AndroidManifest.xml is missing', 'rebuild the archive')
        缓存1523 = {}
        for 步骤698 in 数据728:
            if re.match('classes\\d*\\.dex$', 步骤698):
                try:
                    缓存1523[步骤698] = 键1023.read(步骤698)
                except Exception:
                    pass
        索引1524 = None
        if 'resources.arsc' in 数据728:
            try:
                索引1524 = 键1023.read('resources.arsc')
            except Exception:
                索引1524 = None
    if 结果1522 is not None:
        条目1253 = 步骤578(结果1522)
        if not 条目1253['parses']:
            add('bad', 'manifest-parse', 'AndroidManifest.xml does not parse as binary xml', 'rebuild with apktool or APKEditor · the manifest is damaged')
        else:
            数据1208 = 条目1253.get('package') or ''
            if not 数据1208 or '.' not in 数据1208:
                add('bad', 'package-name', "package name is invalid · '%s'" % 数据1208, 'must contain at least one dot and valid java identifiers')
            if 条目1253['is_split']:
                add('bad', 'split', 'this is a split apk (split=%s)' % 条目1253['split_name'], 'install the whole set, or merge it into one apk')
            if 条目1253['is_split_required']:
                add('bad', 'split-required', 'android:isSplitRequired=true', 'run: arpxtool app.apk diagnose --fix-split')
            if 条目1253['required_split_types'] or 条目1253['split_types']:
                add('bad', 'split-types', 'requiredSplitTypes or splitTypes present', 'run: arpxtool app.apk diagnose --fix-split')
            if 条目1253['split_meta']:
                add('bad', 'split-meta', 'split metadata present · ' + ', '.join(条目1253['split_meta'][:3]), 'rebuild with a proper merge')
            索引884 = 变量280(结果1522) or {}
            if 索引884.get('test_only'):
                add('bad', 'test-only', 'android:testOnly=true · the system refuses it outside adb install -t', 'clear testOnly in the manifest')
            if not 索引884.get('has_application'):
                add('bad', 'application', 'no <application> element · nothing to launch', 'rebuild the manifest')
            路径1646 = 索引884.get('version_code')
            if 路径1646 in (None, '?', '0'):
                add('warn', 'version-code', 'versionCode is missing or zero', 'some installers reject it · set a positive versionCode')
            if not 索引884.get('launcher') or 索引884.get('launcher') == '?':
                add('warn', 'launcher', 'no launcher activity', 'the app installs but shows no icon')
            if not 条目1253['has_uses_sdk']:
                add('warn', 'uses-sdk', 'no <uses-sdk> element', 'android defaults to 1 · external apksigner cannot read minSdkVersion')
            标记1370 = 索引884.get('min_sdk')
            if 参数881 and str(标记1370).isdigit() and (int(标记1370) > int(参数881)):
                add('bad', 'min-sdk', 'minSdkVersion %s is higher than the device sdk %s' % (标记1370, 参数881), 'INSTALL_FAILED_OLDER_SDK · this build cannot run on that device')
            列表1647 = 索引884.get('target_sdk')
            if 参数881 and str(列表1647).isdigit() and (int(列表1647) > int(参数881) + 3):
                add('warn', 'target-sdk', 'targetSdkVersion %s is newer than the device %s' % (列表1647, 参数881), 'usually installs, but behaviour may differ')
            if 索引884.get('shared_user_id'):
                add('warn', 'shared-uid', 'sharedUserId is set · ' + str(索引884.get('shared_user_id')), 'INSTALL_FAILED_SHARED_USER_INCOMPATIBLE if the signature differs')
            数据1648 = 索引884.get('permissions') or []
            状态1649 = {值1062 for 值1062 in 数据1648 if 数据1648.count(值1062) > 1}
            if 状态1649:
                add('warn', 'duplicate-permission', '%d permission(s) declared twice' % len(状态1649), 'harmless on most devices, rejected by some')
            标记1650 = 索引884.get('provider_authorities') or []
            队列1651 = {队列691 for 队列691 in 标记1650 if 标记1650.count(队列691) > 1}
            if 队列1651:
                add('bad', 'provider-authority', 'duplicate provider authority · ' + list(队列1651)[0][:50], 'INSTALL_FAILED_CONFLICTING_PROVIDER')
    路径1246 = 文本548(字节747)
    if 路径1246['status'] == 'stale':
        add('bad', 'signature', 'stale signature block · ' + 路径1246['detail'], 'run: arpxtool app.apk repair')
    elif 路径1246['status'] == 'none':
        add('bad', 'signature', 'not signed', 'run: arpxtool app.apk sign')
    elif 路径1246['status'] == 'v1':
        add('bad', 'signature', 'v1 only · android 11 and later refuse it', 'run: arpxtool app.apk sign')
    if 索引1524 is None:
        add('bad', 'resources', 'resources.arsc is missing', 'rebuild the resources')
    else:
        偏移974 = 值262(索引1524)
        if not 偏移974.valid:
            add('bad', 'resources-parse', 'resources.arsc does not parse', 'the resource table is damaged · rebuild')
        区块855 = 队列291(键743)
        计数1525 = next((修补958 for 修补958 in 区块855 if 修补958['name'] == 'resources.arsc'), None)
        if 计数1525:
            if 计数1525['method'] != 0:
                add('bad', 'resources-stored', 'resources.arsc is compressed', 'store it uncompressed')
            if 计数1525['offset'] % 4:
                add('bad', 'resources-aligned', 'resources.arsc is not 4 byte aligned', 're-align the archive')
    if not 缓存1523:
        add('bad', 'dex', 'no dex payload', 'rebuild the archive')
    else:
        for name, 表744 in 缓存1523.items():
            映射1652 = 源580(表744)
            if not 映射1652.get('magic'):
                add('bad', 'dex-magic', '%s is not a dex file' % name, 'the payload is corrupt')
                continue
            if 映射1652.get('checksum_ok') is False:
                add('bad', 'dex-checksum', '%s fails its adler32 checksum' % name, 'the dex was edited without fixing the header · rewrite it')
            if 映射1652.get('signature_ok') is False:
                add('warn', 'dex-signature', '%s fails its sha1 signature' % name, 'most runtimes ignore this, some verifiers do not')
            if 映射1652.get('version') and 映射1652['version'] > '041':
                add('warn', 'dex-version', '%s declares dex %s' % (name, 映射1652['version']), 'very new dex versions need a recent runtime')
        if len(缓存1523) > 1:
            索引884 = 变量280(结果1522) if 结果1522 else None
            标记1370 = (索引884 or {}).get('min_sdk')
            if str(标记1370).isdigit() and int(标记1370) < 21:
                add('bad', 'multidex', '%d dex files but minSdkVersion %s has no native multidex' % (len(缓存1523), 标记1370), 'add the multidex support library or raise minSdkVersion')
    条目1093 = [修补958 for 修补958 in 队列291(键743) if 修补958['name'].endswith('.so')]
    if 条目1093:
        索引1044 = {}
        for 修补958 in 条目1093:
            变量760 = 修补958['name'].split('/')
            if len(变量760) >= 3 and 变量760[0] == 'lib':
                索引1044.setdefault(变量760[1], []).append(修补958)
        if abi and abi not in 索引1044:
            add('bad', 'abi-missing', 'no native libraries for %s · archive has %s' % (abi, ', '.join(索引1044) or 'none'), 'INSTALL_FAILED_NO_MATCHING_ABIS · add that abi or use a universal build')
        for 条目1653, 区块895 in 索引1044.items():
            关闭1434 = [修补958 for 修补958 in 区块895 if 修补958['method'] != 0]
            if 关闭1434:
                add('bad', 'native-compressed', '%d native object(s) in %s are compressed · install fails with res=-2' % (len(关闭1434), 条目1653), 'run: arpxtool app.apk fix-native')
            偏移1654 = [修补958 for 修补958 in 区块895 if 修补958['method'] == 0 and 修补958['offset'] % 4096]
            if 偏移1654:
                add('warn', 'native-align-4k', '%d .so in %s are not page aligned' % (len(偏移1654), 条目1653), 'matters when extractNativeLibs=false')
    elif abi:
        add('warn', 'no-native', 'no native libraries at all', 'fine for pure java apps')
    if not 检查830:
        add('info', 'clean', 'no install blockers found', '')
    return 检查830
表584 = {('Ljava/lang/System;', 'exit'): ('terminate', 'System.exit'), ('Ljava/lang/Runtime;', 'halt'): ('terminate', 'Runtime.halt'), ('Landroid/os/Process;', 'killProcess'): ('terminate', 'Process.killProcess'), ('Landroid/app/Activity;', 'finish'): ('close', 'Activity.finish'), ('Landroid/app/Activity;', 'finishAndRemoveTask'): ('close', 'finishAndRemoveTask'), ('Landroid/app/Activity;', 'finishAffinity'): ('close', 'finishAffinity'), ('Ljava/lang/System;', 'runFinalizersOnExit'): ('terminate', 'runFinalizersOnExit')}
行585 = {('Landroid/content/pm/PackageManager;', 'getPackageInfo'): 'reads its own signature', ('Landroid/content/pm/PackageManager;', 'getPackageArchiveInfo'): 'reads a signature from a file', ('Landroid/content/pm/PackageManager;', 'getInstallerPackageName'): 'checks the installer', ('Landroid/content/pm/PackageManager;', 'getInstallSourceInfo'): 'checks the installer', ('Ljava/security/MessageDigest;', 'getInstance'): 'hashes something', ('Ljava/util/zip/CRC32;', 'update'): 'checksums something', ('Ljava/util/zip/ZipFile;', '<init>'): 'opens an archive', ('Ldalvik/system/DexFile;', 'loadDex'): 'loads a dex at runtime', ('Ljava/lang/ClassLoader;', 'loadClass'): 'loads a class by name', ('Landroid/content/Context;', 'getPackageCodePath'): 'reads its own apk path', ('Landroid/content/pm/Signature;', 'toByteArray'): 'reads the certificate bytes', ('Landroid/content/pm/Signature;', 'hashCode'): 'compares the certificate hash'}
列586 = {('Ljava/lang/Runtime;', 'exec'): 'runs a shell command', ('Landroid/os/Debug;', 'isDebuggerConnected'): 'detects a debugger', ('Landroid/os/Build;', '<clinit>'): 'reads device fingerprints', ('Ljava/io/File;', 'exists'): 'probes for a path'}

def 字节587(区块815, 参数721, 结果882):
    try:
        键863 = 区块815.m_off + 结果882 * 8
        cls = 区块815.type_name(区块255(参数721, 键863))
        name = 区块815.string(句柄256(参数721, 键863 + 4))
        return (cls or '?', name or '?')
    except Exception:
        return ('?', '?')

def 文本588(参数721, 偏移814, 路径846=None, 缓存883=None):
    区块815 = 写入311(参数721)
    if not 区块815.ok:
        return []
    步骤978 = []
    limit = min(区块815.c_n, 路径846 or 40000)
    for 读取912 in range(limit):
        if 缓存883 is not None and time.time() > 缓存883:
            break
        名字829 = 区块815.c_off + 读取912 * 32
        映射852 = 区块815.type_name(句柄256(参数721, 名字829))
        目标1141 = 句柄256(参数721, 名字829 + 24)
        if not 目标1141 or not 映射852:
            continue
        try:
            索引1444, 值1062 = 步骤258(参数721, 目标1141)
            计数1445, 值1062 = 步骤258(参数721, 值1062)
            路径1446, 值1062 = 步骤258(参数721, 值1062)
            列表1447, 值1062 = 步骤258(参数721, 值1062)
            for 读取1112 in range(索引1444 + 计数1445):
                读取1112, 值1062 = 步骤258(参数721, 值1062)
                读取1112, 值1062 = 步骤258(参数721, 值1062)
            for 列866, 变量1720 in ((路径1446, True), (列表1447, False)):
                结果882 = 0
                for 读取1112 in range(列866):
                    文本1108, 值1062 = 步骤258(参数721, 值1062)
                    结果882 += 文本1108
                    读取1112, 值1062 = 步骤258(参数721, 值1062)
                    栈819, 值1062 = 步骤258(参数721, 值1062)
                    if not 栈819:
                        continue
                    读取1712 = 区块815.method_name(结果882) or '?'
                    缓存923, 读取1112 = 打开393(参数721, 栈819)
                    for 行1665 in 缓存923:
                        路径1686 = 行1665.get('ref')
                        if 路径1686 is None:
                            continue
                        cls, name = 字节587(区块815, 参数721, 路径1686)
                        key = (cls, name)
                        if key in 偏移814:
                            步骤978.append({'class': 映射852, 'method': 读取1712, 'pc': 行1665.get('pc'), 'callee': '%s->%s' % (cls.strip('L;'), name), 'kind': 偏移814[key]})
        except Exception:
            continue
    return 步骤978

def 名字589(索引884):
    文本708 = []
    if not 索引884:
        return 文本708
    for key in ('application_class', 'launcher'):
        标记730 = 索引884.get(key)
        if 标记730 and 标记730 not in ('?', 'None'):
            文本708.append(标记730)
    return 文本708

def 检查590(队列811, name, 修补878):
    if not name:
        return None
    句柄1256 = name
    if 句柄1256.startswith('.'):
        句柄1256 = 修补878 + 句柄1256
    elif '.' not in 句柄1256:
        句柄1256 = 修补878 + '.' + 句柄1256
    节点1257 = 句柄1256.replace('.', '/')
    for 步骤1258 in ('L' + 节点1257 + ';',):
        if 步骤1258 in 队列811:
            return True
    return False
写入591 = re.compile('^\\s*at\\s+([\\w$.]+)\\.([\\w$<>]+)\\(([^)]*)\\)')
读取592 = re.compile('^(?:FATAL EXCEPTION:\\s*)?([\\w$.]+(?:Exception|Error|Throwable)[\\w$]*)(?::\\s*(.*))?$')
打开593 = re.compile('^Caused by:\\s*([\\w$.]+)(?::\\s*(.*))?$')

def 关闭594(text):
    队列1371, 路径1526, 打开713, 列表1527 = (None, '', [], [])
    for 字节747 in text.splitlines():
        计数885 = 字节747.rstrip()
        句柄776 = 写入591.match(计数885)
        if 句柄776:
            cls, 读取1472, 扫描1477 = (句柄776.group(1), 句柄776.group(2), 句柄776.group(3))
            打开713.append({'class': cls, 'method': 读取1472, 'where': 扫描1477, 'file': 扫描1477.split(':')[0] if ':' in 扫描1477 else 扫描1477, 'line': 扫描1477.split(':')[1] if 扫描1477.count(':') >= 1 else ''})
            continue
        映射1132 = 打开593.match(计数885.strip())
        if 映射1132:
            列表1527.append({'type': 映射1132.group(1), 'message': 映射1132.group(2) or ''})
            continue
        修补958 = 读取592.match(计数885.strip())
        if 修补958 and 队列1371 is None:
            队列1371 = 修补958.group(1)
            路径1526 = 修补958.group(2) or ''
    return {'exception': 队列1371, 'message': 路径1526, 'frames': 打开713, 'causes': 列表1527}
构建595 = ('java.', 'javax.', 'kotlin.', 'android.', 'androidx.', 'dalvik.', 'com.android.', 'com.google.android.', 'sun.', 'libcore.')

def 解析596(cls):
    return any((cls.startswith(值1062) for 值1062 in 构建595))

def 扫描597(键743, 打开713):
    队列811 = {}
    try:
        with zipfile.ZipFile(键743) as 键1023:
            for name in 键1023.namelist():
                if re.match('classes\\d*\\.dex$', name):
                    表744 = 键1023.read(name)
                    区块815 = 写入311(表744)
                    if not 区块815.ok:
                        continue
                    for cls in 路径686(表744):
                        队列811[cls.strip('L;').replace('/', '.')] = (name, 表744)
    except Exception:
        return []
    文本708 = []
    for 栈1259 in 打开713:
        info = {'class': 栈1259['class'], 'method': 栈1259['method'], 'line': 栈1259['line'], 'framework': 解析596(栈1259['class']), 'in_apk': False, 'dex': None, 'code': None, 'exists': None}
        读取872 = 队列811.get(栈1259['class'])
        if 读取872:
            info['in_apk'] = True
            info['dex'] = 读取872[0]
            表744 = 读取872[1]
            try:
                行745 = 列表487(表744, 'L' + 栈1259['class'].replace('.', '/') + ';', 栈1259['method'])
                info['code'] = 行745
                info['exists'] = 行745 is not None
            except Exception:
                info['exists'] = None
        文本708.append(info)
    return 文本708
修补598 = re.compile('^\\d{2}-\\d{2}\\s+\\d{2}:\\d{2}:\\d{2}\\.\\d{3}\\s+\\d+\\s+\\d+\\s+[VDIWEF]\\s+[^:]+:\\s?')

def 报告599(计数885):
    return 修补598.sub('', 计数885)

def 变量600(text, 修补878=None):
    源1260 = []
    current = None
    for 目标1261 in text.splitlines():
        计数885 = 报告599(目标1261)
        if 'FATAL EXCEPTION' in 计数885:
            if current:
                源1260.append(current)
            current = [计数885]
            continue
        if current is not None:
            列1506 = 计数885.strip()
            if 列1506.startswith('at ') or 列1506.startswith('Caused by') or 'Exception' in 列1506 or ('Error' in 列1506) or 列1506.startswith('Process:') or 列1506.startswith('\t') or (列1506 == ''):
                current.append(计数885)
                continue
            if len(current) > 2:
                源1260.append(current)
            current = None
    if current:
        源1260.append(current)
    if 修补878:
        参数1481 = [映射692 for 映射692 in 源1260 if any((修补878 in 目标1421 for 目标1421 in 映射692))]
        if 参数1481:
            return 参数1481
    return 源1260

def 参数601(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    结果82('read crash report')
    状态729, 键1383 = 条目573(args.input)
    if not 状态729.exists():
        键63.bad('input not found · ' + str(args.input))
        return 2
    text = 状态729.read_text(encoding='utf-8', errors='replace')
    if zipfile.is_zipfile(状态729):
        with zipfile.ZipFile(状态729) as 键1023:
            字节947 = [步骤698 for 步骤698 in 键1023.namelist() if 步骤698.endswith('.txt') and 'bugreport' in 步骤698.lower()]
            if not 字节947:
                字节947 = [步骤698 for 步骤698 in 键1023.namelist() if 步骤698.endswith('.txt')]
            if 字节947:
                text = 键1023.read(字节947[0]).decode('utf-8', 'replace')
                键63.info('read ' + 字节947[0] + ' from the archive')
    值1262 = getattr(args, '修补878', None)
    if 值1262 or 'FATAL EXCEPTION' in text:
        text = '\n'.join((报告599(目标1421) for 目标1421 in text.splitlines()))
        源1260 = 变量600(text, 值1262)
        if 源1260:
            text = '\n'.join(源1260[0])
            if len(源1260) > 1:
                键63.info('%d crash block(s) found · showing the first' % len(源1260))
    键1263 = 关闭594(text)
    键743 = None
    if args.crash_apk:
        键743, 读取1112 = 条目573(args.crash_apk)
    键63.head('crash report', 行25)
    键63.kv('file', 状态729.name, width=16)
    键63.kv('exception', 键1263['exception'] or '?', width=16)
    if 键1263['message']:
        键63.kv('message', 节点57(键1263['message'], 60), width=16)
    键63.kv('frames', len(键1263['frames']), width=16)
    表1264 = 扫描597(键743, 键1263['frames']) if 键743 else []
    行1265 = [句柄776 for 句柄776 in 表1264 if 句柄776['in_apk']]
    列1266 = [句柄776 for 句柄776 in 表1264 if 句柄776['framework']]
    if 键1263['causes']:
        键63.head('causes', 字节27)
        for 映射1132 in 键1263['causes'][:6]:
            键63.bullet('%s%s' % (映射1132['type'], ': ' + 节点57(映射1132['message'], 60) if 映射1132['message'] else ''))
    键63.head('frames', 文本28)
    if not 表1264:
        for 栈1259 in 键1263['frames'][:40]:
            映射732 = 'framework' if 解析596(栈1259['class']) else 'library'
            写入791 = 打开33 if 映射732 == 'framework' else 构建35
            print('  ' + 写入791(标记50) + ' ' + 修补38('%s.%s' % (栈1259['class'], 栈1259['method'])) + 打开33('  [%s]' % 映射732))
        if len(键1263['frames']) > 40:
            键63.info('%d more frame(s)' % (len(键1263['frames']) - 40))
    for 读取912, 句柄776 in enumerate(表1264[:40]):
        if 句柄776['in_apk']:
            区块1095 = 数据48
            写入791 = 关闭34
            映射732 = 'app'
        elif 句柄776['framework']:
            区块1095 = 标记50
            写入791 = 打开33
            映射732 = 'framework'
        else:
            区块1095 = 标记50
            写入791 = 构建35
            映射732 = 'library'
        读取1312 = ' · ' + 句柄776['dex'] if 句柄776['dex'] else ''
        print('  ' + 写入791(区块1095) + ' ' + 修补38('%s.%s' % (句柄776['class'], 句柄776['method'])) + 打开33('  [%s%s]' % (映射732, 读取1312)))
    if len(表1264) > 40:
        键63.info('%d more frame(s)' % (len(表1264) - 40))
    键63.head('verdict', 文本28 if not 行1265 else 字节27)
    键63.kv('app frames', len(行1265), width=18)
    键63.kv('framework frames', len(列1266), width=18)
    if 行1265:
        数据1528 = 行1265[0]
        键63.kv('first app frame', '%s.%s' % (数据1528['class'], 数据1528['method']), width=16)
        键63.info('this is where your code threw · patch or inspect that method')
        if 数据1528['code']:
            键63.kv('code offset', '0x%x' % 数据1528['code'], width=16)
    elif 键743:
        键63.warn('no frame belongs to this apk · the crash is inside a library or the framework')
    if 键743 is None:
        键63.info('pass --crash-apk app.apk to map frames onto the dex')
    if args.output:
        参数761 = {'exception': 键1263['exception'], 'message': 键1263['message'], 'causes': 键1263['causes'], 'frames': 表1264 or 键1263['frames']}
        行105(Path(args.output).expanduser(), json.dumps(参数761, indent=2), 'w')
        键63.kv('written', str(args.output))
    return 0

def 结果602(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    字节1267 = 字节107('adb')
    键63.head('device crash capture', 行25)
    if not 字节1267:
        键63.warn('adb is not installed')
        键63.info('install it: pkg install android-tools   (or arpxtool install-all --yes)')
        键63.head('manual routes', 字节27)
        print('  ' + 打开33('1. adb logcat -b crash -d          the java stack trace buffer'))
        print('  ' + 打开33('2. adb shell dumpsys dropbox --print data_app_crash'))
        print('  ' + 打开33('3. adb shell dumpsys dropbox --print data_app_anr'))
        print('  ' + 打开33('4. adb bugreport out.zip          everything, including anr traces'))
        键63.info('all four work without root · the shell user holds the dump permission')
        return 3
    数据1208 = args.package
    文本1268 = []
    if args.source in ('crash', 'all'):
        文本1268.append(([字节1267, 'logcat', '-b', 'crash', '-d', '-v', 'threadtime'], 'crash buffer'))
    if args.source in ('dropbox', 'all'):
        文本1268.append(([字节1267, 'shell', 'dumpsys', 'dropbox', '--print', 'data_app_crash'], 'dropbox crash'))
        文本1268.append(([字节1267, 'shell', 'dumpsys', 'dropbox', '--print', 'data_app_anr'], 'dropbox anr'))
    键63.kv('package', 数据1208 or 'any', width=16)
    键63.kv('sources', args.source, width=16)
    名字1269 = []
    for 列706, 修补718 in 文本1268:
        try:
            字节707, 文本708, 名字709 = 检查110(列706, timeout=45)
        except KeyboardInterrupt:
            键63.warn('interrupted')
            return 5
        if 字节707 != 0:
            键63.warn('%s · exit %d' % (修补718, 字节707))
            continue
        值702 = (文本708 or '').splitlines()
        if 数据1208:
            值702 = [目标1421 for 目标1421 in 值702 if 数据1208 in 目标1421 or 目标1421.startswith('\tat ') or 'Caused by' in 目标1421]
        名字1269.append((修补718, 值702))
        键63.ok('%s · %d line(s)' % (修补718, len(值702)))
    键63.head('captured', 文本28)
    total = 0
    for 修补718, 值702 in 名字1269:
        if not 值702:
            continue
        键63.kv(修补718, len(值702), width=16)
        for 计数885 in 值702[:30]:
            print('  ' + 打开33(节点57(计数885, 100)))
        total += len(值702)
    if total and args.output:
        表744 = '\n'.join((目标1421 for 读取1112, 值702 in 名字1269 for 目标1421 in 值702))
        行105(Path(args.output).expanduser(), 表744, 'w')
        键63.kv('written', str(args.output))
    if not total:
        键63.warn('nothing captured · is the device connected and usb debugging on?')
        键63.info('check with: adb devices')
    return 0 if total else 5
缓存603 = '.class public Larp/crash/ArpCrash;\n.super Ljava/lang/Object;\n\n.implements Ljava/lang/Thread$UncaughtExceptionHandler;\n\n.field private static ctx:Landroid/content/Context;\n\n.field private static prev:Ljava/lang/Thread$UncaughtExceptionHandler;\n\n.method public constructor <init>()V\n    .locals 0\n\n    invoke-direct {p0}, Ljava/lang/Object;-><init>()V\n\n    return-void\n.end method\n\n.method public static install()V\n    .locals 3\n\n    :try_start\n    invoke-static {}, Landroid/app/ActivityThread;->currentApplication()Landroid/app/Application;\n\n    move-result-object v0\n\n    sput-object v0, Larp/crash/ArpCrash;->ctx:Landroid/content/Context;\n\n    invoke-static {}, Ljava/lang/Thread;->getDefaultUncaughtExceptionHandler()Ljava/lang/Thread$UncaughtExceptionHandler;\n\n    move-result-object v1\n\n    sput-object v1, Larp/crash/ArpCrash;->prev:Ljava/lang/Thread$UncaughtExceptionHandler;\n\n    new-instance v2, Larp/crash/ArpCrash;\n\n    invoke-direct {v2}, Larp/crash/ArpCrash;-><init>()V\n\n    invoke-static {v2}, Ljava/lang/Thread;->setDefaultUncaughtExceptionHandler(Ljava/lang/Thread$UncaughtExceptionHandler;)V\n    :try_end\n    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :catch_all\n\n    goto :done\n\n    :catch_all\n    move-exception v0\n\n    :done\n    return-void\n.end method\n\n.method public uncaughtException(Ljava/lang/Thread;Ljava/lang/Throwable;)V\n    .locals 10\n\n    :try_start\n    new-instance v0, Ljava/io/StringWriter;\n\n    invoke-direct {v0}, Ljava/io/StringWriter;-><init>()V\n\n    new-instance v1, Ljava/io/PrintWriter;\n\n    invoke-direct {v1, v0}, Ljava/io/PrintWriter;-><init>(Ljava/io/Writer;)V\n\n    invoke-virtual {p2, v1}, Ljava/lang/Throwable;->printStackTrace(Ljava/io/PrintWriter;)V\n\n    invoke-virtual {v1}, Ljava/io/PrintWriter;->flush()V\n\n    new-instance v7, Ljava/lang/StringBuilder;\n\n    invoke-direct {v7}, Ljava/lang/StringBuilder;-><init>()V\n\n    const-string v8, "arpxtool crash report\\n"\n\n    invoke-virtual {v7, v8}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;\n\n    invoke-virtual {v0}, Ljava/io/StringWriter;->toString()Ljava/lang/String;\n\n    move-result-object v8\n\n    invoke-virtual {v7, v8}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;\n\n    invoke-virtual {v7}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;\n\n    move-result-object v2\n\n    const-string v3, "ARPCRASH"\n\n    invoke-static {v3, v2}, Landroid/util/Log;->e(Ljava/lang/String;Ljava/lang/String;)I\n\n    sget-object v3, Larp/crash/ArpCrash;->ctx:Landroid/content/Context;\n\n    if-eqz v3, :skip\n\n    const/4 v4, 0x0\n\n    invoke-virtual {v3, v4}, Landroid/content/Context;->getExternalFilesDir(Ljava/lang/String;)Ljava/io/File;\n\n    move-result-object v4\n\n    if-eqz v4, :skip\n\n    new-instance v5, Ljava/io/File;\n\n    const-string v6, "arpcrash"\n\n    invoke-direct {v5, v4, v6}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V\n\n    invoke-virtual {v5}, Ljava/io/File;->mkdirs()Z\n\n    invoke-static {}, Ljava/lang/System;->currentTimeMillis()J\n\n    move-result-wide v8\n\n    new-instance v6, Ljava/lang/StringBuilder;\n\n    invoke-direct {v6}, Ljava/lang/StringBuilder;-><init>()V\n\n    const-string v4, "crash-"\n\n    invoke-virtual {v6, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;\n\n    invoke-virtual {v6, v8, v9}, Ljava/lang/StringBuilder;->append(J)Ljava/lang/StringBuilder;\n\n    const-string v4, ".txt"\n\n    invoke-virtual {v6, v4}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;\n\n    invoke-virtual {v6}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;\n\n    move-result-object v4\n\n    new-instance v6, Ljava/io/File;\n\n    invoke-direct {v6, v5, v4}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V\n\n    new-instance v5, Ljava/io/FileOutputStream;\n\n    invoke-direct {v5, v6}, Ljava/io/FileOutputStream;-><init>(Ljava/io/File;)V\n\n    invoke-virtual {v2}, Ljava/lang/String;->getBytes()[B\n\n    move-result-object v4\n\n    invoke-virtual {v5, v4}, Ljava/io/FileOutputStream;->write([B)V\n\n    invoke-virtual {v5}, Ljava/io/FileOutputStream;->close()V\n    :try_end\n    .catch Ljava/lang/Throwable; {:try_start .. :try_end} :catch_all\n\n    goto :skip\n\n    :catch_all\n    move-exception v3\n\n    :skip\n    sget-object v3, Larp/crash/ArpCrash;->prev:Ljava/lang/Thread$UncaughtExceptionHandler;\n\n    if-eqz v3, :nodelegate\n\n    invoke-interface {v3, p1, p2}, Ljava/lang/Thread$UncaughtExceptionHandler;->uncaughtException(Ljava/lang/Thread;Ljava/lang/Throwable;)V\n\n    :nodelegate\n    return-void\n.end method\n'

def 索引604(text):
    关闭1114 = []
    if not text.strip().startswith('.class'):
        关闭1114.append('missing .class')
    打开993 = 0
    for 读取912, 计数885 in enumerate(text.splitlines(), 1):
        节点697 = 计数885.strip()
        if 节点697.startswith('.method'):
            打开993 += 1
        elif 节点697.startswith('.end method'):
            打开993 -= 1
            if 打开993 < 0:
                关闭1114.append('unbalanced .end method at line %d' % 读取912)
                打开993 = 0
    if 打开993 != 0:
        关闭1114.append('%d unclosed method block(s)' % 打开993)
    for 映射732 in (':try_start', ':try_end', ':catch_all', ':skip', ':nodelegate', ':done'):
        if 映射732 not in text:
            关闭1114.append('missing label ' + 映射732)
    return 关闭1114

def 计数605(text):
    检查1270 = 0
    current = None
    for 计数885 in text.splitlines():
        节点697 = 计数885.strip()
        if 节点697.startswith('.locals') or 节点697.startswith('.registers'):
            变量760 = 节点697.split()
            if len(变量760) == 2 and 变量760[1].isdigit():
                current = int(变量760[1])
        for 源860 in re.findall('\\bv(\\d+)\\b', 节点697):
            检查1270 = max(检查1270, int(源860))
    return (current, 检查1270)

def 路径606(路径886, 列表887):
    值702 = 路径886.splitlines()
    文本708 = []
    写入1271 = False
    构建1195 = False
    for 计数885 in 值702:
        文本708.append(计数885)
        节点697 = 计数885.strip()
        if 节点697.startswith('.method'):
            构建1195 = True
            continue
        if 节点697.startswith('.end method'):
            构建1195 = False
            continue
        if 构建1195 and (not 写入1271) and (节点697.startswith('.locals') or 节点697.startswith('.registers')):
            文本708.append('')
            文本708.append('    ' + 列表887)
            文本708.append('')
            写入1271 = True
    return ('\n'.join(文本708) + '\n', 写入1271)
列表607 = {8194, 8195, 8196, 8197}
数据608 = {0: 112, 1: 4, 2: 4, 3: 12, 4: 8, 5: 8, 6: 32, 7: 4, 8: 8}

def 状态609(参数721):
    if len(参数721) < 112 or 参数721[:4] != b'dex\n':
        return None
    打开1113 = 句柄256(参数721, 52)
    if 打开1113 <= 0 or 打开1113 + 4 > len(参数721):
        return None
    列866 = 句柄256(参数721, 打开1113)
    if 列866 == 0 or 列866 > 512:
        return None
    文本708 = []
    for 读取912 in range(列866):
        键863 = 打开1113 + 4 + 读取912 * 12
        if 键863 + 12 > len(参数721):
            return None
        状态1529 = 区块255(参数721, 键863)
        关闭914 = 句柄256(参数721, 键863 + 4)
        偏移894 = 句柄256(参数721, 键863 + 8)
        文本708.append((状态1529, 关闭914, 偏移894))
    return 文本708

def 标记610(参数721):
    关闭1114 = []
    if len(参数721) < 112 or 参数721[:4] != b'dex\n':
        return ['not a dex file']
    try:
        区块1255 = 句柄256(参数721, 8)
        映射1212 = zlib.adler32(参数721[12:]) & 4294967295
        if 区块1255 != 映射1212:
            关闭1114.append('header checksum mismatch')
    except Exception:
        关闭1114.append('header unreadable')
    构建795 = 状态609(参数721)
    if 构建795 is None:
        关闭1114.append('map_list missing or unreadable')
        return 关闭1114
    读取1272 = None
    for 状态1529, 关闭914, 偏移894 in 构建795:
        if 状态1529 not in 列表607 and 偏移894 % 4:
            关闭1114.append('section 0x%04x is not 4 byte aligned (0x%x)' % (状态1529, 偏移894))
        if 偏移894 > len(参数721):
            关闭1114.append('section 0x%04x starts past the end of the file' % 状态1529)
            continue
        if 读取1272 is not None and 偏移894 < 读取1272:
            关闭1114.append('sections are out of order at 0x%04x' % 偏移894)
        读取1272 = 偏移894
    for 区块815, (状态1529, 关闭914, 偏移894) in enumerate(构建795):
        区块1415 = 数据608.get(状态1529)
        if not 区块1415 or 关闭914 == 0:
            continue
        end = 偏移894 + 关闭914 * 区块1415
        if end > len(参数721):
            关闭1114.append('section 0x%04x runs past the end of the file' % 状态1529)
            continue
        字节1507 = None
        for 区块1655, 句柄1656, 节点1657 in 构建795:
            if 节点1657 > 偏移894 and (字节1507 is None or 节点1657 < 字节1507):
                字节1507 = 节点1657
        if 字节1507 is None:
            continue
        for 变量1280 in range(end, 字节1507):
            if 参数721[变量1280] != 0:
                关闭1114.append('non-zero padding 0x%02x before section at 0x%x (type 0x%04x)' % (参数721[变量1280], 字节1507, 状态1529))
                break
    return 关闭1114

def 队列611(参数721):
    区块815 = 写入311(参数721)
    if not 区块815.ok:
        return None
    数据728 = set()
    for 读取912 in range(区块815.c_n):
        try:
            name = 区块815.type_name(句柄256(参数721, 区块815.c_off + 读取912 * 32))
            if name:
                数据728.add(name)
        except Exception:
            continue
    return 数据728

def 映射612(键783, 数据888):
    关闭1114 = []
    try:
        标记1530 = {}
        with zipfile.ZipFile(键783) as 步骤1658:
            标记1010 = {}
            for name in 步骤1658.namelist():
                if re.match('classes\\d*\\.dex$', name):
                    表744 = 步骤1658.read(name)
                    标记1010[name] = 队列611(表744)
                    标记1530[name] = set(标记610(表744))
        with zipfile.ZipFile(数据888) as 扫描1437:
            结果1202 = {}
            for name in 扫描1437.namelist():
                if re.match('classes\\d*\\.dex$', name):
                    表744 = 扫描1437.read(name)
                    结果1202[name] = 队列611(表744)
                    区块1455 = 标记1530.get(name, set())
                    for 缓存1763 in 标记610(表744):
                        if 缓存1763 in 区块1455:
                            continue
                        关闭1114.append('%s · %s' % (name, 缓存1763))
    except Exception as 修补958:
        return ['could not compare builds · ' + 节点57(str(修补958), 60)]
    打开1273 = 0
    for name, 数据728 in 标记1010.items():
        if 数据728 is None:
            continue
        行1105 = 结果1202.get(name)
        if 行1105 is None:
            打开1273 += len(数据728)
            关闭1114.append('%s is missing from the rebuilt archive' % name)
            continue
        队列1531 = 数据728 - 行1105
        if 队列1531:
            打开1273 += len(队列1531)
            栈1659 = sorted(队列1531)[:3]
            关闭1114.append('%s lost %d class(es) · e.g. %s' % (name, len(队列1531), ', '.join((映射1132.strip('L;') for 映射1132 in 栈1659))))
    if not 结果1202:
        关闭1114.append('the rebuilt archive has no dex at all')
    return 关闭1114

def 条目613(键783, 数据888, 修补718='rebuild'):
    关闭1274 = 0
    try:
        with zipfile.ZipFile(数据888) as 键1023:
            区块855 = [(读取912, 键1023.read(读取912.filename)) for 读取912 in 键1023.infolist()]
    except Exception as 修补958:
        键63.bad('cannot read the rebuilt archive · ' + 节点57(str(修补958), 60))
        return False
    键1103 = {}
    for info, 表744 in 区块855:
        if not re.match('classes\\d*\\.dex$', info.filename):
            continue
        if not 表744[:4] == b'dex\n':
            continue
    if 键1103:
        扫描797 = Path(str(数据888) + '.fix')
        try:
            with zipfile.ZipFile(数据888) as 名字1429, zipfile.ZipFile(扫描797, 'w') as 检查1430:
                for info in 名字1429.infolist():
                    参数761 = 键1103.get(info.filename, 名字1429.read(info.filename))
                    状态1609 = zipfile.ZipInfo(info.filename, date_time=info.date_time)
                    状态1609.compress_type = info.compress_type
                    状态1609.external_attr = info.external_attr
                    状态1609.internal_attr = info.internal_attr
                    状态1609.create_system = info.create_system
                    检查1430.writestr(状态1609, 参数761)
            os.replace(扫描797, 数据888)
            键63.ok('repaired %d byte(s) of dex padding' % 关闭1274)
        except Exception as 修补958:
            键63.warn('padding repair failed · ' + 节点57(str(修补958), 50))
    return 偏移614(键783, 数据888, 修补718)

def 偏移614(键783, 数据888, 修补718='rebuild'):
    关闭1114 = 映射612(键783, 数据888)
    if not 关闭1114:
        return True
    键63.head('build check', 字节27)
    键63.warn('%s produced a broken archive' % 修补718)
    for 值1062 in 关闭1114[:6]:
        键63.bullet(值1062)
    键63.info('this archive would crash on launch · it is not being kept')
    try:
        Path(数据888).unlink()
    except Exception:
        pass
    键63.info('try the in-place path instead: --strategy surgery')
    return False

def 区块615(变量880):
    try:
        if hasattr(变量880, 'read') and hasattr(变量880, 'namelist'):
            数据728 = 变量880.namelist()
            if 'AndroidManifest.xml' not in 数据728:
                return (None, {})
            return (变量880.read('AndroidManifest.xml'), 变量280(变量880.read('AndroidManifest.xml')) or {})
        变量720 = Path(变量880)
        with zipfile.ZipFile(变量720) as 键1023:
            if 'AndroidManifest.xml' not in 键1023.namelist():
                return (None, {})
            字节747 = 键1023.read('AndroidManifest.xml')
        return (字节747, 变量280(字节747) or {})
    except Exception:
        return (None, {})

def 句柄616(状态889, 写入751):
    变量720, 键1383 = 条目573(状态889)
    if 变量720 is None:
        return (None, None, 键1383)
    try:
        with zipfile.ZipFile(变量720) as 键1023:
            数据728 = 键1023.namelist()
    except Exception:
        return (变量720, None, None)
    if 'AndroidManifest.xml' in 数据728:
        return (变量720, None, None)
    构建1275 = [步骤698 for 步骤698 in 数据728 if 步骤698.lower().endswith('.apk')]
    if not 构建1275:
        return (变量720, None, None)
    列表767 = 节点617(变量720, 写入751)
    if 列表767:
        return (列表767, 'merged %d split(s) into one apk' % len(构建1275), None)
    键863, name = 步骤618(变量720, 写入751)
    if name:
        return (键863, 'bundle · used %s (splits were not merged)' % name, None)
    return (变量720, None, None)

def 节点617(变量840, 写入751):
    扫描757 = 构建195(Path(写入751), allow_net=False, 缓存723=True)
    文本708 = Path(写入751) / 'merged.apk'
    解析1276 = 扫描757.get('apkeditor')
    if 解析1276:
        try:
            字节707, 读取1112 = 关闭114(列186(解析1276) + ['m', '-i', str(变量840), '-o', str(文本708), '-f'], 'merge splits', timeout=2400)
            if 字节707 == 0 and 文本708.exists() and (文本708.stat().st_size > 1024):
                with zipfile.ZipFile(文本708) as 键1023:
                    if 'AndroidManifest.xml' in 键1023.namelist():
                        return 文本708
        except Exception:
            pass
    扫描1277 = 扫描757.get('apktool')
    if 扫描1277:
        try:
            字节707, 读取1112 = 关闭114(列186(扫描1277) + ['d', '-f', '-s', '-r', str(变量840), '-o', str(Path(写入751) / 'bundle_src')], 'apktool decode bundle', timeout=2400)
        except Exception:
            字节707 = -1
    return None

def 步骤618(变量720, 写入751):
    变量720 = Path(变量720)
    try:
        with zipfile.ZipFile(变量720) as 键1023:
            数据728 = 键1023.namelist()
            if 'AndroidManifest.xml' in 数据728:
                return (变量720, None)
            名字869 = [步骤698 for 步骤698 in 数据728 if 步骤698.lower().endswith('.apk')]
            if not 名字869:
                return (变量720, None)
            键863 = [步骤698 for 步骤698 in 名字869 if Path(步骤698).name.lower() == 'base.apk']
            计数1045 = 键863 + [步骤698 for 步骤698 in 名字869 if 步骤698 not in 键863]
            for name in 计数1045:
                try:
                    表744 = 键1023.read(name)
                except Exception:
                    continue
                if 表744[:2] != b'PK':
                    continue
                try:
                    with zipfile.ZipFile(io.BytesIO(表744)) as 字节947:
                        if 'AndroidManifest.xml' not in 字节947.namelist():
                            continue
                except Exception:
                    continue
                dest = Path(写入751) / (Path(name).name or 'base.apk')
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(表744)
                return (dest, name)
    except Exception:
        return (变量720, None)
    return (变量720, None)

def 栈619(字节787):
    for 键863 in sorted(Path(字节787).glob('smali*')):
        if not 键863.is_dir():
            continue
        for file in 键863.rglob('*.smali'):
            try:
                head = file.read_text(encoding='utf-8', errors='replace')[:2000]
            except Exception:
                continue
            if '.super Landroid/app/Application;' in head:
                修补1278 = file.relative_to(键863).with_suffix('')
                return 'L' + '/'.join(修补1278.parts) + ';'
    return None

def 源620(字节787, skip=()):
    for 键863 in sorted(Path(字节787).glob('smali*')):
        if not 键863.is_dir():
            continue
        for file in 键863.rglob('*.smali'):
            try:
                text = file.read_text(encoding='utf-8', errors='replace')
            except Exception:
                continue
            if 'Larp/crash/ArpCrash;' in text:
                continue
            if '.method protected onCreate(Landroid/os/Bundle;)V' in text or '.method public onCreate(Landroid/os/Bundle;)V' in text:
                修补1278 = file.relative_to(键863).with_suffix('')
                return 'L' + '/'.join(修补1278.parts) + ';'
    return None

def 目标621(字节787, 队列891):
    修补1278 = 队列891.strip('L;')
    关闭794 = 修补1278 + '.smali'
    for 键863 in sorted(Path(字节787).glob('smali*')):
        if not 键863.is_dir():
            continue
        步骤1258 = 键863 / 关闭794
        if 步骤1258.exists():
            return 步骤1258
    return None

def 值622(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    键743, 键1383 = 条目573(args.input)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        return 2
    if not 句柄536(['java', 'apktool'], 'smali injection'):
        键63.bad('apktool is required to add the crash handler')
        键63.info('run: arpxtool install-all --yes')
        return 3
    扫描757 = 构建195(键743.parent, allow_net=False, 缓存723=True)
    if not 扫描757.get('apktool'):
        键63.bad('apktool not available')
        return 3
    写入751 = Path(tempfile.mkdtemp())
    try:
        键743, 字节947 = 步骤618(键743, 写入751)
        if 字节947:
            键63.info('bundle detected · using ' + 字节947)
        索引884 = {}
        try:
            with zipfile.ZipFile(键743) as 键1023:
                if 'AndroidManifest.xml' in 键1023.namelist():
                    索引884 = 区块615(键1023)[1] or {}
        except Exception:
            索引884 = {}
        修补878 = 索引884.get('package') or ''
        路径806 = []
        if 索引884.get('application_class'):
            路径806.append(索引884['application_class'])
        if 索引884.get('launcher') and 索引884.get('launcher') not in (None, '?'):
            路径806.append(索引884['launcher'])
        键63.head('crash handler injection', 行25)
        键63.kv('package', 修补878 or 'unreadable', width=16)
        键63.kv('manifest targets', ', '.join((条目693 for 条目693 in 路径806 if 条目693)) or 'none', width=16)
        状态729 = 写入751 / 'src'
        字节707, 源1660 = 关闭114(列186(扫描757['apktool']) + ['d', '-f', '-s', '-r', str(键743), '-o', str(状态729)], 'apktool decode', timeout=1800)
        if 字节707 != 0 or not 状态729.exists():
            键63.bad('apktool could not decode this archive')
            键63.info('the archive may be packed or protected')
            return 6
        映射1532 = 状态729 / 'smali' / 'arp' / 'crash'
        映射1532.mkdir(parents=True, exist_ok=True)
        关闭1114 = 索引604(缓存603)
        if 关闭1114:
            键63.bad('generated handler failed its own check · ' + ', '.join(关闭1114))
            return 6
        行105(映射1532 / 'ArpCrash.smali', 缓存603.encode('utf-8'), 'wb')
        键63.ok('handler written · arp/crash/ArpCrash.smali')
        if not 路径806:
            目标1661 = 栈619(状态729)
            if 目标1661:
                路径806.append(目标1661)
                键63.ok('found application class in smali · ' + 目标1661)
            else:
                参数1721 = 源620(状态729)
                if 参数1721:
                    路径806.append(参数1721)
                    键63.ok('found a class with onCreate · ' + 参数1721)
        if not 路径806:
            键63.warn('no manifest targets and no Application class in smali')
        写入1271 = []
        for 字节747 in 路径806:
            if not 字节747:
                continue
            if 字节747.startswith('L') and 字节747.endswith(';'):
                队列891 = 字节747
                映射852 = 字节747.strip('L;').replace('/', '.')
            else:
                映射852 = 字节747
                if 映射852.startswith('.'):
                    映射852 = 修补878 + 映射852
                elif '.' not in 映射852:
                    映射852 = 修补878 + '.' + 映射852
                队列891 = 'L' + 映射852.replace('.', '/') + ';'
            变量720 = 目标621(状态729, 队列891)
            if not 变量720:
                键63.warn('class not found in smali · ' + 映射852)
                continue
            text = 变量720.read_text(encoding='utf-8', errors='replace')
            结果1722, 句柄1456 = 路径606(text, 'invoke-static {}, Larp/crash/ArpCrash;->install()V')
            if not 句柄1456:
                键63.warn('no method body to hook · ' + 映射852)
                continue
            行105(变量720, 结果1722.encode('utf-8'), 'wb')
            写入1271.append(映射852)
            键63.ok('hooked ' + 映射852)
        if not 写入1271:
            键63.bad('could not hook any class · nothing to build')
            return 6
        dest = Path(args.output).expanduser() if args.output else 映射572(键743, 'crashlog')
        字节707, 源1660 = 关闭114(列186(扫描757['apktool']) + ['b', str(状态729), '-o', str(dest)], 'apktool build', timeout=1800)
        if 字节707 != 0 or not dest.exists():
            键63.bad('apktool could not rebuild the archive')
            return 6
        条目293(dest)
        if not args.unsigned:
            ok, 目标1501 = 路径206(扫描757, dest, 写入751, args.password)
            键63.kv('signed', 目标1501 if ok else 'no signer')
        键63.head('done', 文本28)
        键63.kv('output', str(dest))
        键63.kv('hooked', len(写入1271), width=16)
        print('  ' + 打开33('after it crashes, the trace is written to:'))
        print('  ' + 打开33('/sdcard/Android/data/%s/files/arpcrash/' % (修补878 or '<pkg>')))
        print('  ' + 打开33('read it with: arpxtool <file>.txt crash-read --crash-apk ' + 键743.name))
        return 0
    finally:
        shutil.rmtree(写入751, ignore_errors=True)

def 键623(参数721):
    打开793 = []
    if len(参数721) < 12:
        return 打开793
    打开793.append(('header', 区块255(参数721, 0), 区块255(参数721, 2), 句柄256(参数721, 4)))
    行745 = 区块255(参数721, 2)
    end = min(len(参数721), 句柄256(参数721, 4))
    列986 = 0
    while 行745 + 8 <= end and 列986 < 4000:
        列986 += 1
        写入1351 = 区块255(参数721, 行745)
        打开913 = 区块255(参数721, 行745 + 2)
        读取1352 = 句柄256(参数721, 行745 + 4)
        打开793.append(('0x%04x' % 写入1351, 打开913, 读取1352, 行745))
        if 读取1352 < 8 or 行745 + 读取1352 > len(参数721):
            行745 += 4
            continue
        行745 += 读取1352
    return 打开793

def 表624(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    写入751 = Path(tempfile.mkdtemp())
    键743, note, 条目1533 = 句柄616(args.input, 写入751)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        return 2
    if note:
        键63.info(note)
    字节747, 索引884 = 区块615(键743)
    if 字节747 is None:
        键63.bad('no AndroidManifest.xml in this archive')
        return 3
    键63.head('binary xml', 行25)
    键63.kv('file', Path(键743).name, width=14)
    键63.kv('bytes', len(字节747), width=14)
    报告1079 = 报告279(字节747)
    键63.kv('parses', 'yes' if 报告1079.valid else 'no', width=14)
    键63.kv('strings', len(报告1079.pool.items) if 报告1079.pool else 0, width=14)
    键63.kv('attributes read', len(报告1079.attrs), width=14)
    键63.kv('package', 索引884.get('package', '?'), width=14)
    if 索引884.get('package_recovered'):
        键63.warn('package came from the string pool, not from the manifest attribute')
    键63.head('chunks', 文本28)
    for 行705, 打开913, 读取1352, 行745 in 键623(字节747)[:40]:
        print('  ' + 打开33('%-8s hdr %-4d size %-8d at 0x%x' % (行705, 打开913, 读取1352, 行745)))
    键63.info('send these lines if the manifest does not parse')
    return 0

def 行625(键743):
    索引924 = []
    try:
        with zipfile.ZipFile(键743) as 键1023:
            for info in 键1023.infolist():
                if not info.filename.endswith('.so'):
                    continue
                if info.compress_type != zipfile.ZIP_STORED:
                    索引924.append(('compressed', info.filename))
                缓存1723 = info.header_offset + 30 + len(info.filename.encode()) + len(info.extra)
                if 缓存1723 % 4096:
                    索引924.append(('unaligned', info.filename))
    except Exception:
        return []
    return 索引924

def 列626(键743, dest):
    try:
        with zipfile.ZipFile(键743) as 名字1429, zipfile.ZipFile(dest, 'w') as 检查1430:
            for 区块1415 in 名字1429.infolist():
                行1705 = 区块1415.filename.upper()
                if 行1705.startswith('META-INF/') and 行1705.endswith(('.SF', '.RSA', '.DSA', '.EC', '.MF')):
                    continue
                参数761 = 名字1429.read(区块1415.filename)
                状态1609 = zipfile.ZipInfo(区块1415.filename, date_time=区块1415.date_time)
                修补1438 = 区块1415.filename.endswith('.so') or 区块1415.filename == 'resources.arsc'
                状态1609.compress_type = zipfile.ZIP_STORED if 修补1438 else 区块1415.compress_type
                状态1609.external_attr = 区块1415.external_attr
                状态1609.internal_attr = 区块1415.internal_attr
                状态1609.create_system = 区块1415.create_system
                检查1430.writestr(状态1609, 参数761)
    except Exception as 修补958:
        键63.bad('could not rewrite the archive · ' + 节点57(str(修补958), 60))
        return False
    条目293(dest, 报告799=4, 变量800=4096)
    return True

def 字节627(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    写入751 = Path(tempfile.mkdtemp())
    键743, note, 条目1533 = 句柄616(args.input, 写入751)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        return 2
    if note:
        键63.info(note)
    标记1010 = 行625(键743)
    键63.head('native libraries', 行25)
    键63.kv('file', Path(键743).name, width=16)
    键63.kv('objects', sum((1 for 读取912 in zipfile.ZipFile(键743).infolist() if 读取912.filename.endswith('.so'))), width=16)
    键63.kv('problems', len(标记1010), width=16)
    if not 标记1010:
        键63.ok('every native object is stored and page aligned')
        return 0
    报告1279 = {}
    for 行705, 偏移1534 in 标记1010:
        报告1279[行705] = 报告1279.get(行705, 0) + 1
    for 行705, 列866 in 报告1279.items():
        键63.warn('%d %s' % (列866, 'compressed object(s)' if 行705 == 'compressed' else 'unaligned object(s)'))
    dest = Path(args.output).expanduser() if args.output else 映射572(键743, 'native')
    if not 列626(键743, dest):
        return 6
    结果1202 = 行625(dest)
    键63.head('result', 文本28)
    键63.kv('output', str(dest))
    键63.kv('problems', len(结果1202), width=16)
    if 结果1202:
        键63.bad('still %d problem(s) after the rewrite' % len(结果1202))
        return 6
    键63.ok('all native objects are stored and aligned to 4096')
    if not getattr(args, 'unsigned', False):
        扫描757 = 构建195(dest.parent, allow_net=False, 缓存723=True)
        ok, 目标1501 = 路径206(扫描757, dest, dest.parent, getattr(args, '缓存763', 'arpxtool'))
        键63.kv('signed', 目标1501 if ok else 'no signer')
    键63.info('INSTALL_FAILED_INVALID_APK with res=-2 is usually this')
    return 0

def 文本628(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    键743, 标记1250 = 条目573(args.input)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        return 2
    写入751 = Path(tempfile.mkdtemp())
    键743, note, 键1383 = 句柄616(键743, 写入751)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        return 2
    if note:
        键63.info(note)
    字节747, 索引884 = 区块615(键743)
    if 字节747 is None:
        键63.bad('this archive has no readable AndroidManifest.xml')
        键63.info('it may be a bundle · try: arpxtool <file> diagnose')
        return 3
    键63.head('crash capture patch', 行25)
    键63.kv('file', 键743.name, width=16)
    键63.kv('package', 索引884.get('package') or '?', width=16)
    键63.kv('debuggable', 'yes' if 索引884.get('debuggable') else 'no', width=16)
    缓存1363, 步骤978 = 名字629(字节747)
    if not 缓存1363:
        键63.warn('could not set debuggable in the manifest')
    else:
        键63.ok('android:debuggable=true written')
    dest = Path(args.output).expanduser() if args.output else 映射572(键743, 'crashlog')
    名字669(键743, dest, {'AndroidManifest.xml': 缓存1363} if 缓存1363 else {}, args)
    键63.head('how to read the crash', 文本28)
    键63.kv('output', str(dest))
    数据1208 = 索引884.get('package') or 'your.package'
    print('  ' + 打开33('1. install the patched build'))
    print('  ' + 打开33('2. connect usb, enable debugging'))
    print('  ' + 打开33('3. arpxtool logcat --package ' + 数据1208))
    print('  ' + 打开33('4. arpxtool crash.txt crash-read --crash-apk ' + dest.name))
    键63.info('debuggable makes android print the full stack trace instead of closing silently')
    return 0

def 名字629(参数721):
    报告1079 = 报告279(参数721)
    if not 报告1079.valid:
        return (None, 0)
    变量1280 = 打开633(参数721, 'debuggable', 'application')
    if 变量1280 is not None:
        文本708 = bytearray(参数721)
        文本708[变量1280 - 1] = 18
        struct.pack_into('<I', 文本708, 变量1280, 1)
        return (bytes(文本708), 1)
    列946 = 步骤338(参数721)
    if 列946.ok and 列946.pool_index is not None:
        键1103 = 列946.patch_application([('debuggable', 18, 1)])
        if 键1103:
            文本708 = 列946.serialize()
            if 文本708 and 报告279(文本708).valid:
                return (文本708, len(键1103))
    return (None, 0)

def 检查630(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    写入751 = Path(tempfile.mkdtemp())
    键743, note, 标记1250 = 句柄616(args.input, 写入751)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        for 字节787 in (标记1250 or [])[:5]:
            键63.info('looked in ' + str(字节787))
        return 2
    if note:
        键63.info(note)
    with zipfile.ZipFile(键743) as 键1023:
        数据728 = 键1023.namelist()
        结果1522 = 区块615(键1023)[0]
        缓存1523 = [键1023.read(步骤698) for 步骤698 in 数据728 if re.match('classes\\d*\\.dex$', 步骤698)]
    索引884 = 变量280(结果1522) if 结果1522 else {}
    修补878 = (索引884 or {}).get('package') or ''
    键63.head('startup triage', 行25)
    键63.kv('file', 键743.name, width=16)
    键63.kv('package', 修补878 or '?', width=16)
    键63.kv('dex files', len(缓存1523), width=16)
    参数1281 = set()
    for 表744 in 缓存1523:
        参数1281.update(路径686(表744))
    键63.kv('classes', len(参数1281), width=16)
    区块1535, 句柄1536, 节点1537 = ([], [], [])
    for 表744 in 缓存1523:
        区块1535.extend(文本588(表744, 表584))
        句柄1536.extend(文本588(表744, 行585))
        节点1537.extend(文本588(表744, 列586))
    结果1282 = []
    状态1209 = []
    for name in 名字589(索引884):
        路径1246 = 检查590(参数1281, name, 修补878)
        if 路径1246 is False:
            状态1209.append(name)
    if 状态1209:
        结果1282.append(('critical', 'missing-class', 'the manifest names a class that is not in the dex: ' + ', '.join(状态1209[:3]), 'the app crashes before it draws anything'))
    缓存1283 = [解析956 for 解析956 in 区块1535 if 解析956['kind'] == 'terminate']
    if 缓存1283:
        步骤1538 = {}
        for 解析956 in 缓存1283:
            步骤1538.setdefault(解析956['class'], []).append(解析956)
        结果1282.append(('high', 'self-terminate', '%d call site(s) that kill the process, in %d class(es)' % (len(缓存1283), len(步骤1538)), 'run signature-engine, or patch these sites with edit'))
    索引1284 = [解析956 for 解析956 in 句柄1536 if 'signature' in 解析956['kind'] or 'certificate' in 解析956['kind']]
    if 索引1284:
        队列811 = {解析956['class'] for 解析956 in 索引1284}
        结果1282.append(('high', 'signature-check', '%d call site(s) reading the app signature, in %d class(es)' % (len(索引1284), len(队列811)), 'the app compares its certificate and exits when it differs'))
    计数1285 = [解析956 for 解析956 in 句柄1536 if 解析956['kind'] in ('hashes something', 'checksums something')]
    if 计数1285:
        结果1282.append(('medium', 'integrity-hash', '%d call site(s) hashing or checksumming' % len(计数1285), 'a changed dex or apk changes the digest and can abort startup'))
    if 节点1537:
        结果1282.append(('medium', 'environment-probe', '%d call site(s) probing the environment' % len(节点1537), 'root, debugger or emulator checks can exit deliberately'))
    if len(缓存1523) > 1:
        结果1282.append(('medium', 'multidex', '%d dex files · the application class must be in the first one' % len(缓存1523), 'if the startup class lives in classes2.dex the process dies at once'))
    变量1200 = [步骤698 for 步骤698 in 数据728 if 步骤698.endswith('.so')]
    if 变量1200:
        索引1044 = sorted({步骤698.split('/')[1] for 步骤698 in 变量1200 if 步骤698.startswith('lib/') and 步骤698.count('/') >= 2})
        结果1282.append(('info', 'native', '%d native object(s) across %s' % (len(变量1200), ', '.join(索引1044) or '?'), 'a missing abi or a mismatched libflutter/libapp pair crashes at launch'))
    键63.head('likely causes', 文本28 if not 结果1282 else 字节27)
    if not 结果1282:
        键63.ok('nothing in the dex suggests a deliberate exit')
    计数1045 = {'critical': 0, 'high': 1, 'medium': 2, 'info': 3}
    for 区块775, code, 表704, 数据928 in sorted(结果1282, key=lambda 名字909: 计数1045.get(名字909[0], 9)):
        区块1095 = {'critical': 状态49, 'high': 状态49, 'medium': '!', 'info': 标记50}.get(区块775, 标记50)
        写入791 = {'critical': 解析36, 'high': 解析36, 'medium': 构建35, 'info': 打开33}.get(区块775, 打开33)
        print('  ' + 写入791(区块1095) + ' ' + 修补38(code) + ' ' + 打开33('· ' + 表704))
        if 数据928:
            print('      ' + 打开33('why  ' + 数据928))
    if 缓存1283 or 索引1284:
        键63.head('where', 字节27)
        栈1539 = 0
        for 解析956 in (索引1284 + 缓存1283)[:12]:
            键63.bullet('%s->%s · pc %s · %s' % (解析956['class'], 解析956['method'], 解析956['pc'], 解析956['callee']))
            栈1539 += 1
        total = len(索引1284) + len(缓存1283)
        if total > 栈1539:
            键63.info('%d more site(s)' % (total - 栈1539))
    键63.head('verdict', 文本28 if not 结果1282 else 字节27)
    键63.kv('kill sites', len(缓存1283), width=16)
    键63.kv('signature reads', len(索引1284), width=16)
    键63.kv('hash sites', len(计数1285), width=16)
    if args.output:
        参数761 = {'reasons': 结果1282, 'terminate': 区块1535, 'integrity': 句柄1536, 'detect': 节点1537}
        行105(Path(args.output).expanduser(), json.dumps(参数761, indent=2), 'w')
        键63.kv('written', str(args.output))
    return 0

def 写入631(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    键743, 标记1250 = 条目573(args.input)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        for 字节787 in (标记1250 or [])[:5]:
            键63.info('looked in ' + str(字节787))
        return 2
    if args.fix_split:
        键743, 字节947 = 步骤618(键743, Path(tempfile.mkdtemp()))
        if 字节947:
            键63.info('bundle detected · using ' + 字节947)
        字节747, 值1662 = 区块615(键743)
        if 字节747 is None:
            键63.bad('no readable manifest in this archive')
            return 3
        缓存1363, 键1103 = 读取632(字节747)
        if not 缓存1363:
            键63.bad('nothing to fix in the manifest')
            return 5
        dest = Path(args.output).expanduser() if args.output else 映射572(键743, 'unsplit')
        名字669(键743, dest, {'AndroidManifest.xml': 缓存1363}, args)
        键63.head('fixed', 文本28)
        键63.kv('removed', ', '.join(键1103), width=14)
        键63.kv('output', str(dest))
        结果1202 = 栈579(dest)
        bad = [读取952 for 读取952 in 结果1202 if 读取952[0] == 'bad']
        键63.kv('remaining', len(bad), width=14)
        return 0
    键743, 字节947 = 步骤618(键743, Path(tempfile.mkdtemp()))
    if 字节947:
        键63.info('bundle detected · inspecting ' + 字节947)
    检查830 = 键583(键743, getattr(args, '参数881', None), getattr(args, 'abi', None))
    键63.head('install diagnosis', 行25)
    键63.kv('file', 键743.name, width=16)
    条目1253 = 步骤578(区块615(键743)[0] or b'')
    键63.kv('package', 条目1253.get('package') or '?', width=16)
    键63.kv('base apk', 'no · split=' + str(条目1253.get('split_name')) if 条目1253['is_split'] else 'yes', width=16)
    键63.kv('min sdk', 条目1253.get('min_sdk') or '?', width=16)
    bad = [读取952 for 读取952 in 检查830 if 读取952[0] == 'bad']
    warn = [读取952 for 读取952 in 检查830 if 读取952[0] == 'warn']
    info = [读取952 for 读取952 in 检查830 if 读取952[0] == 'info']
    键63.head('problems', 文本28 if not bad else 字节27)
    if info and (not bad) and (not warn):
        键63.ok('nothing found that would block an install')
    for 区块775, code, 表704, 数据928 in 检查830:
        (键63.bad if 区块775 == 'bad' else 键63.warn)('%s · %s' % (code, 表704))
        if 数据928:
            print('      ' + 打开33('fix  ' + 数据928))
    键63.head('verdict', 文本28 if not bad else 字节27)
    键63.kv('checks run', 41, width=16)
    键63.kv('blocking', len(bad), width=16)
    键63.kv('warnings', len(warn), width=16)
    if bad:
        键63.info('a clean app shows zero blocking problems · this one has %d' % len(bad))
    return 0 if not bad else 5

def 读取632(参数721):
    报告1079 = 报告279(参数721)
    if not 报告1079.valid:
        return (None, [])
    键1103 = []
    文本708 = bytearray(参数721)
    for 队列1411, 映射1412, 节点1417, 偏移1414 in 报告1079.attrs:
        if 映射1412 != 'manifest':
            continue
        表944 = 节点577(节点1417)
        if 表944 == 'isSplitRequired' and 偏移1414 == 'true':
            变量1280 = 打开633(参数721, 表944, 'manifest')
            if 变量1280 is not None:
                struct.pack_into('<I', 文本708, 变量1280, 0)
                键1103.append('isSplitRequired')
        elif 表944 in ('splitTypes', 'requiredSplitTypes') and 偏移1414:
            变量1280 = 打开633(参数721, 表944, 'manifest')
            if 变量1280 is not None:
                文本708[变量1280 - 1] = 0
                struct.pack_into('<I', 文本708, 变量1280, 0)
                键1103.append(表944)
    if not 键1103:
        return (None, [])
    try:
        源1540 = 报告279(bytes(文本708))
        if not 源1540.valid:
            return (None, [])
    except Exception:
        return (None, [])
    return (bytes(文本708), 键1103)

def 打开633(参数721, name, 映射892=None):
    报告1079 = 报告279(参数721)
    if not 报告1079.valid or not 报告1079.pool:
        return None
    区块815 = None
    for 读取912, 区块1415 in enumerate(报告1079.pool.items):
        if 节点577(区块1415) == name:
            区块815 = 读取912
            break
    if 区块815 is None:
        return None
    行745 = 区块255(参数721, 2)
    end = min(len(参数721), 句柄256(参数721, 4))
    列986 = 0
    while 行745 + 8 <= end and 列986 < 400000:
        列986 += 1
        写入1351 = 区块255(参数721, 行745)
        读取1352 = 句柄256(参数721, 行745 + 4)
        if 读取1352 < 8:
            break
        if 写入1351 == 258:
            键863 = 行745 + 16
            文本748 = 句柄256(参数721, 键863 + 4)
            if 映射892 is None or 报告1079.pool.get(文本748) == 映射892:
                数据1408 = 区块255(参数721, 键863 + 8) or 20
                状态1409 = 区块255(参数721, 键863 + 10) or 20
                列866 = 区块255(参数721, 键863 + 12)
                for 读取912 in range(min(列866, 64)):
                    队列691 = 键863 + 数据1408 + 读取912 * 状态1409
                    if 句柄256(参数721, 队列691 + 4) == 区块815:
                        return 队列691 + 16
        行745 += 读取1352
    return None

def 关闭634(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    键743, 标记1250 = 条目573(args.input)
    if 键743 is None:
        键63.bad('input not found · ' + args.input)
        for 字节787 in (标记1250 or [])[:6]:
            键63.info('looked in ' + str(字节787))
        return 2
    路径1246 = 文本548(键743.read_bytes())
    修补878 = 标记570(键743)
    列表1287 = None
    try:
        参数721 = 键743.read_bytes()
        句柄1216 = 值542(参数721)
        表744 = 句柄1216.get(1896449818) or 句柄1216.get(4031998144)
        if 表744:
            解析1716, 读取1112 = 键543(表744, 0)
            扫描1717, 读取1112 = 键543(解析1716, 0)
            修补1718, 行745 = 键543(扫描1717, 0)
            索引1724, 行745 = 键543(修补1718, 0)
            打开1233, 读取1112 = 键543(修补1718, 行745)
            计数1725, 读取1112 = 键543(打开1233, 0)
            列表1287 = hashlib.sha256(计数1725).hexdigest().upper()
    except Exception:
        列表1287 = None
    键63.head('identity', 行25)
    键63.kv('file', 键743.name, width=14)
    键63.kv('package', 修补878 or '?', width=14)
    键63.kv('signature', 路径1246['status'], width=14)
    键63.kv('schemes', ', '.join(路径1246['schemes']) or 'none', width=14)
    if 列表1287:
        键63.kv('cert sha256', 列表1287[:32] + '...', width=14)
    数据1288 = 状态569(列表1287)
    键63.head('origin', 文本28 if 数据1288 else 字节27)
    if 数据1288:
        数据1208, 读取872 = 数据1288
        键63.ok('signed by arpxtool')
        键63.kv('original', 数据1208, width=14)
        键63.kv('keystore', Path(读取872.get('keystore', '')).name, width=14)
        if 读取872.get('updated'):
            键63.kv('last build', 读取872['updated'], width=14)
    elif 修补878 and 修补878 in 路径566().get('apps', {}):
        读取872 = 路径566()['apps'][修补878]
        键63.info('a key exists for this package but the signature does not match it')
        键63.kv('keystore', Path(读取872.get('keystore', '')).name, width=14)
    else:
        键63.info('not signed by arpxtool · original signature')
    return 0

def 构建635(args):
    键743, 标记1250 = 条目573(args.input)
    if 键743 is None:
        键63.bad('input not found · ' + args.input)
        return 2
    修补878 = args.alias or 标记570(键743)
    if not 修补878:
        修补878 = re.sub('[^A-Za-z0-9._-]', '_', 键743.stem) or 'unknown'
        键63.warn('manifest has no package · using the file name')
        键63.kv('package', 修补878, width=14)
    dest = 队列571(修补878)
    计数565()
    键63.head('per app key', 行25)
    键63.kv('app', 键743.name, width=14)
    键63.kv('package', 修补878, width=14)
    键63.kv('keystore', str(dest), width=14)
    if dest.exists() and (not args.overwrite):
        键63.ok('key already exists · reused')
    else:
        条目1013 = argparse.Namespace(output=str(dest), 打开873=修补878, 缓存763=args.password, dname='CN=%s, OU=%s, O=%s, C=IN' % (修补878, 索引564, 索引564), validity=args.validity or 10000, keysize=args.keysize or 2048, overwrite=True, 缓存723=True, yes=True)
        字节707 = 扫描637(条目1013)
        if 字节707 != 0:
            return 字节707
    key, 解析876 = 修补558(dest)
    列表1287 = None
    if 解析876 is not None:
        列表1287 = hashlib.sha256(解析876.public_bytes(__import__('cryptography').hazmat.primitives.serialization.Encoding.DER)).hexdigest().upper()
    数据568(修补878, dest, 列表1287, 键743)
    键63.head('registered', 文本28)
    键63.kv('cert sha256', (列表1287 or '?')[:32] + '...', width=14)
    键63.info('sign with: arpxtool %s sign' % 键743.name)
    return 0

def 解析636():
    try:
        __import__('cryptography')
        return True
    except Exception:
        return False

def 扫描637(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    dest = Path(args.output).expanduser() if args.output else HOME / 'arp-release.keystore'
    打开873 = args.alias or 'arp'
    缓存763 = args.password or 'arpxtool'
    状态1289 = args.dname or 'CN=ARP Release, OU=Android, O=ARPX, C=IN'
    标记1290 = args.validity or 10000
    队列1291 = args.keysize or 2048
    if dest.exists() and (not args.overwrite):
        键63.warn('keystore already exists · ' + str(dest))
        键63.info('use --overwrite to replace it, or --output to pick another name')
        打开553({'keystore': str(dest), 'alias': 打开873, 'store_pass': 缓存763})
        键63.kv('remembered', 'this keystore is now the default')
        return 0
    键63.head('key generation', 行25)
    键63.kv('keystore', str(dest), width=14)
    键63.kv('alias', 打开873, width=14)
    键63.kv('algorithm', 'RSA %d' % 队列1291, width=14)
    键63.kv('validity', '%d days' % 标记1290, width=14)
    映射1292 = False
    if 字节107('keytool') and (not 解析636()):
        dest.parent.mkdir(parents=True, exist_ok=True)
        字节707, 文本708, 名字709 = 检查110(['keytool', '-genkeypair', '-keystore', str(dest), '-alias', 打开873, '-keyalg', 'RSA', '-keysize', str(队列1291), '-sigalg', 'SHA256withRSA', '-validity', str(标记1290), '-storepass', 缓存763, '-keypass', 缓存763, '-dname', 状态1289, '-storetype', 'PKCS12'], timeout=300)
        if 字节707 == 0 and dest.exists():
            映射1292 = True
            键63.ok('created with keytool · PKCS12')
        else:
            键63.warn('keytool failed · ' + 节点57((名字709 or 文本708 or '').strip(), 80))
    if not 映射1292:
        try:
            from cryptography.hazmat.primitives import hashes, serialization
            from cryptography.hazmat.primitives.asymmetric import rsa
            from cryptography import x509
            from cryptography.x509.oid import NameOID
            from cryptography.hazmat.primitives.serialization import pkcs12
            import datetime
            key = rsa.generate_private_key(public_exponent=65537, key_size=队列1291)
            偏移734 = []
            for 键1663 in 状态1289.split(','):
                if '=' not in 键1663:
                    continue
                名字989, 步骤818 = 键1663.split('=', 1)
                名字989, 步骤818 = (名字989.strip().upper(), 步骤818.strip())
                路径1726 = {'CN': NameOID.COMMON_NAME, 'OU': NameOID.ORGANIZATIONAL_UNIT_NAME, 'O': NameOID.ORGANIZATION_NAME, 'C': NameOID.COUNTRY_NAME, 'L': NameOID.LOCALITY_NAME, 'ST': NameOID.STATE_OR_PROVINCE_NAME}.get(名字989)
                if 路径1726:
                    偏移734.append(x509.NameAttribute(路径1726, 步骤818))
            name = x509.Name(偏移734 or [x509.NameAttribute(NameOID.COMMON_NAME, 'ARP')])
            行1105 = datetime.datetime.utcnow()
            解析876 = x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key()).serial_number(x509.random_serial_number()).not_valid_before(行1105 - datetime.timedelta(days=1)).not_valid_after(行1105 + datetime.timedelta(days=标记1290)).add_extension(x509.BasicConstraints(ca=True, path_length=None), critical=True).sign(key, hashes.SHA256())
            表744 = pkcs12.serialize_key_and_certificates(打开873.encode(), key, 解析876, None, serialization.BestAvailableEncryption(缓存763.encode()))
            dest.parent.mkdir(parents=True, exist_ok=True)
            行105(dest, 表744, 'wb')
            表1664 = dest.with_suffix('.pem')
            行105(表1664, key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()), 'wb')
            行105(dest.with_suffix('.crt'), 解析876.public_bytes(serialization.Encoding.PEM), 'wb')
            映射1292 = True
            键63.ok('created with python · PKCS12')
            键63.kv('pem key', str(表1664))
        except Exception as 修补958:
            键63.bad('generation failed · ' + 节点57(str(修补958), 70))
            键63.info('install java for keytool: pkg install openjdk-17')
            return 3
    try:
        os.chmod(dest, 384)
    except Exception:
        pass
    列表1287 = 关闭554(dest, 缓存763, 打开873)
    打开553({'keystore': str(dest), 'alias': 打开873, 'store_pass': 缓存763, 'key_pass': 缓存763})
    键63.head('result', 文本28)
    键63.kv('keystore', str(dest), width=14)
    键63.kv('size', 表104(dest.stat().st_size), width=14)
    if 列表1287:
        键63.kv('sha256', 列表1287, width=14)
    键63.kv('remembered', 'now the default for signing')
    键63.info('sign with: arpxtool app.apk sign')
    return 0

def 修补638(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    键743, 键1383 = 条目573(args.input)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    映射1252 = 读取552()
    if not args.keystore:
        区块1055 = 区块575(键743, args.password)
        if 区块1055:
            键63.info('using the key made for ' + 区块1055)
            映射1252 = {}
    if args.keystore:
        索引204['keystore'] = args.keystore
        索引204['alias'] = args.alias or 映射1252.get('alias') or 'arp'
        索引204['store_pass'] = args.store_pass or 映射1252.get('store_pass')
        索引204['key_pass'] = args.key_pass or 索引204['store_pass']
    elif 映射1252.get('keystore'):
        索引204['keystore'] = 映射1252['keystore']
        索引204['alias'] = 映射1252.get('alias') or 'arp'
        索引204['store_pass'] = 映射1252.get('store_pass')
        索引204['key_pass'] = 映射1252.get('key_pass') or 映射1252.get('store_pass')
    else:
        键63.warn('no keystore yet')
        键63.info('create one: arpxtool keygen')
        return 3
    值1022 = Path(索引204['keystore']).expanduser()
    if not 值1022.exists():
        键63.bad('keystore not found · ' + str(值1022))
        键63.info('create one: arpxtool keygen')
        return 3
    路径1246 = 文本548(键743.read_bytes())
    键63.head('sign', 行25)
    键63.kv('archive', 键743.name, width=14)
    键63.kv('keystore', 值1022.name, width=14)
    键63.kv('alias', 索引204['alias'], width=14)
    键63.kv('before', 路径1246['status'], width=14)
    if 路径1246['status'] == 'stale':
        键63.info('a stale block will be replaced')
        列1506, 句柄1056 = 名字549(键743.read_bytes())
        if 句柄1056:
            行105(键743, 列1506, 'wb')
            键63.ok('removed the stale block first')
    条目293(键743)
    扫描757 = 构建195(键743.parent, allow_net=False, 缓存723=True)
    ok, 目标1501 = 路径206(扫描757, 键743, 键743.parent, args.password)
    映射772 = 文本548(键743.read_bytes())
    键63.head('result', 文本28 if ok else 字节27)
    键63.kv('signed by', 目标1501 if ok else 'none', width=14)
    键63.kv('state', 映射772['status'], width=14)
    键63.kv('schemes', ', '.join(映射772['schemes']) or 'none', width=14)
    if 映射772['status'] == 'valid':
        键63.ok('this archive is installable')
        return 0
    if 映射772['status'] == 'v1':
        键63.warn('v1 only · android 11 and later need v2 or v3')
        键63.info('install apksigner: pkg install apksigner')
        return 5
    键63.bad('signing did not produce a valid signature')
    return 7

def 报告639(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    状态729, 键1383 = 条目573(args.input)
    if 状态729 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    字节747 = 状态729.read_bytes()
    路径1246 = 文本548(字节747)
    键63.head('signature state', 行25)
    键63.kv('archive', 状态729.name, width=16)
    键63.kv('size', 表104(len(字节747)), width=16)
    键63.kv('schemes', ', '.join(路径1246['schemes']) or 'none', width=16)
    if 路径1246['status'] == 'valid':
        键63.ok('signature is valid · nothing to repair')
        if not getattr(args, 'force_repair', False):
            return 0
    elif 路径1246['status'] == 'stale':
        键63.bad('stale signature block · ' + 路径1246['detail'])
        键63.info('embedded ' + 路径1246['embedded'][:32] + '...')
        键63.info('computed ' + 路径1246['computed'][:32] + '...')
        键63.info('this is why the archive cannot install')
    elif 路径1246['status'] == 'none':
        键63.warn('no signing block present')
    else:
        键63.warn(路径1246['detail'])
    列1506, 句柄1056 = 名字549(字节747)
    if 句柄1056:
        键63.ok('removed the apk signing block')
    else:
        键63.info('no signing block to remove')
    check = 文本548(列1506)
    if check['status'] != 'none':
        键63.warn('block still present after strip · ' + check['detail'])
    扫描797 = Path(tempfile.mkdtemp())
    try:
        计数1365 = 扫描797 / 'stripped.apk'
        行105(计数1365, 列1506, 'wb')
        目标1541 = 句柄296(计数1365)
        if 目标1541:
            键63.ok('removed %d stale META-INF file(s)' % 目标1541)
        条目293(计数1365)
        键63.ok('re-aligned entries')
        dest = Path(args.output).expanduser() if args.output else 映射572(状态729, 'repaired')
        shutil.copy2(计数1365, dest)
        区块1055 = 区块575(状态729, args.password)
        if 区块1055:
            键63.info('signing with the key made for ' + 区块1055)
        if not args.unsigned:
            扫描757 = 构建195(扫描797, allow_net=False, 缓存723=True)
            ok, 目标1501 = 路径206(扫描757, dest, 扫描797, args.password)
            键63.kv('signed', 目标1501 if ok else 'no signer available')
            if not ok:
                键63.warn('sign it manually before installing')
        值1542 = 文本548(dest.read_bytes())
        键63.head('result', 文本28)
        键63.kv('output', str(dest))
        键63.kv('state', 值1542['status'], width=16)
        键63.kv('schemes', ', '.join(值1542['schemes']) or 'none', width=16)
        if 值1542['status'] == 'valid':
            键63.ok('this archive is now installable')
        elif 值1542['status'] == 'none':
            键63.warn('unsigned · sign it before installing')
        else:
            键63.bad('still not valid · ' + 值1542['detail'])
        return 0
    finally:
        shutil.rmtree(扫描797, ignore_errors=True)

def 变量640(args):
    缓存3.probe()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    标记1210, 索引284, 映射1212, ok = 节点537()
    键63.head('build identity', 行25)
    for key in ('app', 'version', 'codename', 'author', 'channel'):
        键63.kv(key, 标记1210.get(key, '?'), width=14)
    键63.head('integrity', 文本28 if ok else 字节27)
    键63.kv('seal', 索引284[:32] + '...', width=14)
    if ok:
        键63.ok('identity record is intact')
    else:
        键63.warn('identity record has been modified')
        键63.info('expected ' + 映射1212[:32] + '...')
    状态729 = Path(__file__).resolve()
    try:
        节点1057 = hashlib.sha256(状态729.read_bytes()).hexdigest()
        键63.head('source', 行25)
        键63.kv('file', 状态729.name, width=14)
        键63.kv('sha256', 节点1057, width=14)
        键63.kv('bytes', 表104(状态729.stat().st_size), width=14)
        键63.info('this hash identifies this exact build')
    except Exception:
        pass
    键63.head('notice', 字节27)
    print('  ' + 打开33('This tool is provided under the MIT licence with the copyright'))
    print('  ' + 打开33('notice preserved in LICENSE. Removing the identity record from a'))
    print('  ' + 打开33('copy is permitted by the licence only if the notice is kept.'))
    return 0 if ok else 4

def 参数641(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    打开793 = 队列531()
    状态1209 = [名字909 for 名字909 in 打开793 if not 名字909['present']]
    键63.head('full stack', 行25)
    键63.kv('present', '%d of %d' % (len(打开793) - len(状态1209), len(打开793)), width=16)
    if not 状态1209:
        键63.ok('every tool is already installed')
        return 0
    数据1208 = 字节107('pkg') or 字节107('apt-get') or 字节107('apt')
    参数1201 = 字节107('pip') or 字节107('pip3')
    修补798 = []
    for 名字909 in 状态1209:
        if 名字909['kind'] == 'module' and 参数1201:
            修补798.append([参数1201, 'install', 'pyyaml' if 名字909['name'] == 'yaml' else 名字909['name']])
        elif 名字909['kind'] == 'binary' and 名字909['name'] in 缓存643 and 数据1208:
            修补798.append([数据1208, 'install', '-y', 缓存643[名字909['name']]])
    句柄1096, 区块1295 = (set(), [])
    for 结果762 in 修补798:
        key = tuple(结果762)
        if key not in 句柄1096:
            句柄1096.add(key)
            区块1295.append(结果762)
    键63.head('plan', 字节27)
    键63.kv('packages', len(区块1295), width=16)
    for 结果762 in 区块1295:
        print('    ' + 打开33(' '.join(结果762)))
    条目1293 = [名字909 for 名字909 in 状态1209 if 名字909['kind'] == 'jar']
    if 条目1293:
        键63.kv('jars', ', '.join((名字909['name'] for 名字909 in 条目1293)), width=16)
    if not args.yes:
        键63.head('dry run', 字节27)
        键63.info('nothing installed - rerun with --yes to execute')
        return 0
    键63.head('installing', 文本28)
    ok = 0
    for 结果762 in 区块1295:
        字节707, 读取1112 = 关闭114(结果762, 'install ' + 结果762[-1], timeout=2400)
        if 字节707 == 0:
            ok += 1
            键63.ok(结果762[-1])
        else:
            键63.warn('failed - ' + 结果762[-1])
    if 条目1293:
        扫描757 = 构建195(Path.cwd(), allow_net=True, 缓存723=True)
        for 名字909 in 条目1293:
            if 名字909['name'].startswith('apktool') and 扫描757.get('apktool'):
                ok += 1
                键63.ok('apktool')
            elif 名字909['name'].startswith('uber') and 扫描757.get('uber'):
                ok += 1
                键63.ok('uber-apk-signer')
            elif 名字909['name'].startswith('apkeditor') and 扫描757.get('apkeditor'):
                ok += 1
                键63.ok('apkeditor')
    键63.head('result', 文本28)
    映射772 = 队列531()
    偏移1294 = sum((1 for 名字909 in 映射772 if 名字909['present']))
    键63.kv('available', '%d of %d' % (偏移1294, len(映射772)), width=16)
    键63.info('restart the shell so new binaries land on PATH')
    return 0

def 结果642(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    打开793 = 队列531()
    键63.head('external tools', 行25)
    for 名字909 in 打开793:
        区块1095 = 数据48 if 名字909['present'] else 状态49 if 名字909['critical'] else 标记50
        写入791 = 关闭34 if 名字909['present'] else 解析36 if 名字909['critical'] else 构建35
        计数885 = '%-22s %s' % (名字909['name'], 名字909['purpose'])
        print('  ' + 写入791(区块1095) + ' ' + 修补38(计数885))
        if not 名字909['present'] and 名字909['hint']:
            print('      ' + 打开33('install  ' + 名字909['hint']))
        elif 名字909['present'] and 名字909['path']:
            print('      ' + 打开33(节点57(名字909['path'], 72)))
    偏移1294 = sum((1 for 名字909 in 打开793 if 名字909['present']))
    状态1209 = [名字909 for 名字909 in 打开793 if not 名字909['present']]
    键63.head('summary', 文本28)
    键63.kv('available', '%d of %d' % (偏移1294, len(打开793)), width=18)
    键63.kv('missing', len(状态1209), width=18)
    if 状态1209:
        键63.info('run: arpxtool setup --yes')
    if args.output:
        行105(Path(args.output).expanduser(), json.dumps(打开793, indent=2), 'w')
        键63.kv('written', str(args.output))
    return 0
缓存643 = {'java': 'openjdk-17', 'keytool': 'openjdk-17', 'aapt2': 'aapt2', 'apksigner': 'apksigner', 'unzip': 'unzip', 'zip': 'zip', 'adb': 'android-tools', 'file': 'file', 'strings': 'binutils', 'readelf': 'binutils', 'objdump': 'binutils'}

def 索引644(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    打开793 = [名字909 for 名字909 in 队列531() if not 名字909['present']]
    键63.head('setup', 行25)
    if not 打开793:
        键63.ok('everything already present')
        return 0
    数据1208 = 字节107('pkg') or 字节107('apt') or 字节107('apt-get')
    参数1201 = 字节107('pip') or 字节107('pip3')
    修补798 = []
    for 名字909 in 打开793:
        if 名字909['kind'] == 'module':
            if 参数1201:
                修补798.append([参数1201, 'install', 名字909['name']])
        elif 名字909['kind'] == 'binary' and 名字909['name'] in 缓存643 and 数据1208:
            修补798.append([数据1208, 'install', '-y', 缓存643[名字909['name']]])
    句柄1096 = []
    区块1295 = []
    for 结果762 in 修补798:
        key = tuple(结果762)
        if key not in 句柄1096:
            句柄1096.append(key)
            区块1295.append(结果762)
    if not 区块1295:
        键63.warn('no package manager found · install manually:')
        for 名字909 in 打开793:
            键63.bullet('%s  ·  %s' % (名字909['name'], 名字909['hint']))
        return 3
    键63.kv('packages', len(区块1295), width=18)
    for 结果762 in 区块1295:
        print('    ' + 打开33(' '.join(结果762)))
    if not args.yes:
        键63.head('dry run', 字节27)
        键63.info('nothing installed · rerun with --yes to execute')
        return 0
    键63.head('installing', 文本28)
    ok = 0
    for 结果762 in 区块1295:
        字节707, 读取1112 = 关闭114(结果762, 'install ' + 结果762[-1], timeout=1800)
        if 字节707 == 0:
            ok += 1
            键63.ok(结果762[-1])
        else:
            键63.warn('failed · ' + 结果762[-1])
    键63.head('result', 文本28)
    键63.kv('installed', '%d of %d' % (ok, len(区块1295)), width=18)
    键63.info('restart the shell so new binaries land on PATH')
    return 0
计数645 = (b'ssl_client\x00', b'ssl_server\x00')
路径646 = {'aarch64': struct.pack('<II', 1384120352, 3596551104), 'x86_64': bytes.fromhex('b801000000c3'), 'arm': bytes.fromhex('01207047'), 'x86': bytes.fromhex('b801000000c3')}
列表647 = (2847898621, 3506439167, 2847570941, 2847833085, 3506570239, 3506504703)

def 数据648(参数721, 条目893):
    文本708 = []
    start = 0
    while True:
        读取912 = 参数721.find(条目893, start)
        if 读取912 < 0:
            return 文本708
        文本708.append(读取912)
        start = 读取912 + 1

def 状态649(数据848, 偏移894):
    for 值1502, 键1503, 表1504 in getattr(数据848, 'segments', []):
        if 键1503 <= 偏移894 < 键1503 + 表1504:
            return 值1502 + (偏移894 - 键1503)
    return None

def 标记650(数据848):
    return [(步骤818, 列786, 节点697) for 步骤818, 列786, 节点697 in getattr(数据848, 'segments', [])]

def 队列651(参数721, 数据848):
    句柄1216 = []
    for 值1502, 键1503, 表1504 in 标记650(数据848):
        end = min(键1503 + 表1504, len(参数721)) - 8
        行745 = 键1503
        while 行745 < end:
            行1665 = 句柄256(参数721, 行745)
            if 行1665 & 2667577344 == 2415919104:
                列表1727 = 行1665 >> 29 & 3
                数据1728 = 行1665 >> 5 & 524287
                状态1729 = 数据1728 << 2 | 列表1727
                if 状态1729 & 1 << 20:
                    状态1729 -= 1 << 21
                表864 = 值1502 + (行745 - 键1503)
                变量800 = (表864 & ~4095) + (状态1729 << 12)
                标记1730 = 行1665 & 31
                字节1507 = 句柄256(参数721, 行745 + 4)
                if 字节1507 & 4286578688 == 2432696320:
                    索引1764 = 字节1507 >> 5 & 31
                    计数1765 = 字节1507 & 31
                    if 索引1764 == 标记1730 and 计数1765 == 标记1730:
                        句柄1216.append((行745, 变量800 + (字节1507 >> 10 & 4095)))
            行745 += 4
    return 句柄1216

def 映射652(参数721, 数据848):
    句柄1216 = []
    for 值1502, 键1503, 表1504 in 标记650(数据848):
        end = min(键1503 + 表1504, len(参数721)) - 7
        行745 = 键1503
        while 行745 < end:
            if 参数721[行745] in (72, 76) and 参数721[行745 + 1] == 141:
                if 参数721[行745 + 2] & 199 == 5:
                    路径1766 = struct.unpack_from('<i', 参数721, 行745 + 3)[0]
                    表864 = 值1502 + (行745 - 键1503)
                    句柄1216.append((行745, 表864 + 7 + 路径1766))
                    行745 += 7
                    continue
            行745 += 1
    return 句柄1216

def 条目653(参数721, 数据848, 步骤858):
    条目893 = struct.pack('<I', 步骤858 & 4294967295)
    文本708 = []
    for 值1502, 键1503, 表1504 in 标记650(数据848):
        键1543 = 参数721[键1503:键1503 + 表1504]
        start = 0
        while True:
            读取912 = 键1543.find(条目893, start)
            if 读取912 < 0:
                break
            文本708.append(键1503 + 读取912)
            start = 读取912 + 1
    return 文本708
偏移654 = {步骤818[:4] for 步骤818 in 路径646.values()}

def 区块655(参数721, 数据848, 行745, 路径726):
    limit = max(0, 行745 - 8192)
    if 路径726 == 'aarch64':
        数据1168 = 行745
        while 数据1168 >= limit:
            if 句柄256(参数721, 数据1168) in 列表647:
                return 数据1168
            if bytes(参数721[数据1168:数据1168 + 4]) in 偏移654:
                return 数据1168
            数据1168 -= 4
        return None
    if 路径726 == 'arm':
        数据1168 = 行745 & ~1
        while 数据1168 >= limit:
            if bytes(参数721[数据1168:数据1168 + 4]) in 偏移654:
                return 数据1168
            列1666 = 区块255(参数721, 数据1168)
            if 列1666 & 65280 == 46336 or 列1666 & 65520 == 59680:
                return 数据1168
            数据1168 -= 2
        return None
    数据1168 = 行745
    while 数据1168 >= limit:
        if bytes(参数721[数据1168:数据1168 + 4]) in 偏移654:
            return 数据1168
        映射692 = 参数721[数据1168]
        if 映射692 in (195, 204):
            return 数据1168 + 1
        if 映射692 == 85 and 参数721[数据1168 + 1] == 72 and (参数721[数据1168 + 2] == 137):
            return 数据1168
        if 映射692 == 243 and 参数721[数据1168 + 1] == 15 and (参数721[数据1168 + 2] == 30):
            return 数据1168
        数据1168 -= 1
    return None

def 句柄656(变量720):
    数据848 = 行265(变量720)
    if not 数据848.ok:
        return (None, 'not an elf object')
    try:
        参数721 = Path(变量720).read_bytes()
    except Exception as 修补958:
        return (None, 节点57(str(修补958), 60))
    句柄1296 = {}
    for 条目893 in 计数645:
        步骤978 = 数据648(参数721, 条目893)
        if not 步骤978:
            return (None, 'anchor %s not found' % 条目893.rstrip(b'\x00').decode())
        表1544 = [步骤818 for 步骤818 in (状态649(数据848, 解析956) for 解析956 in 步骤978) if 步骤818]
        if not 表1544:
            return (None, 'anchor outside mapped segments')
        句柄1296[条目893] = set(表1544)
    if 数据848.machine == 'aarch64':
        句柄1216 = 队列651(参数721, 数据848)
    elif 数据848.machine in ('x86_64', 'x86'):
        句柄1216 = 映射652(参数721, 数据848)
    else:
        句柄1216 = []
    节点1297 = {}
    for 条目893, 行1545 in 句柄1296.items():
        标记1130 = set()
        for 行745, 关闭794 in 句柄1216:
            if 关闭794 in 行1545:
                标记1130.add(行745)
        if not 标记1130:
            for 步骤818 in 行1545:
                标记1130.update(条目653(参数721, 数据848, 步骤818))
        节点1297[条目893] = 标记1130
    步骤1298 = {}
    栈1299 = {}
    for 条目893, 标记1130 in 节点1297.items():
        写入991 = set()
        for 行745 in 标记1130:
            start = 区块655(参数721, 数据848, 行745, 数据848.machine)
            if start is not None:
                写入991.add(start)
                栈1299.setdefault(start, 行745)
        步骤1298[条目893] = 写入991
    源1300 = None
    for 写入991 in 步骤1298.values():
        源1300 = 写入991 if 源1300 is None else 源1300 & 写入991
    偏移1134 = []
    for start in sorted(源1300 or []):
        列1546 = bytes(参数721[start:start + 4]) in 偏移654
        偏移1134.append({'ref': '0x%x' % 栈1299.get(start, 0), 'start': '0x%x' % start, 'file_offset': start, 'method': 'already-patched' if 列1546 else 'string-pair'})
    if not 偏移1134:
        for 条目893, 标记1130 in 节点1297.items():
            for 行745 in sorted(标记1130)[:6]:
                start = 区块655(参数721, 数据848, 行745, 数据848.machine)
                偏移1134.append({'ref': '0x%x' % 行745, 'start': '0x%x' % start if start else None, 'file_offset': start, 'method': 'single-anchor'})
    return ({'candidates': 偏移1134, 'machine': 数据848.machine, 'bits': 数据848.bits, 'anchors': {名字989.rstrip(b'\x00').decode(): len(步骤818) for 名字989, 步骤818 in 节点1297.items()}}, None)

def 节点657(变量720, dry=False):
    句柄816, 名字709 = 句柄656(变量720)
    if 句柄816 is None:
        return (False, 名字709, None)
    数据848 = 行265(变量720)
    结果1122 = 路径646.get(数据848.machine)
    if not 结果1122:
        return (False, 'no stub for isa ' + 数据848.machine, 句柄816)
    目标1301 = [映射1132 for 映射1132 in 句柄816['candidates'] if 映射1132.get('file_offset') and 映射1132['method'] == 'string-pair']
    if not 目标1301:
        目标1301 = [映射1132 for 映射1132 in 句柄816['candidates'] if 映射1132.get('file_offset') and 映射1132['method'] == 'already-patched']
    if not 目标1301:
        目标1301 = [映射1132 for 映射1132 in 句柄816['candidates'] if 映射1132.get('file_offset')]
    if not 目标1301:
        return (False, 'anchors found but no prologue resolved', 句柄816)
    关闭794 = 目标1301[0]['file_offset']
    try:
        with open(变量720, 'rb') as 构建915:
            构建915.seek(关闭794)
            键783 = 构建915.read(len(结果1122))
        if 键783 == 结果1122:
            return (True, 'already patched at 0x%x' % 关闭794, 句柄816)
        if not dry:
            计数1165 = Path(str(变量720) + '.arpbak')
            if not 计数1165.exists():
                shutil.copy2(变量720, 计数1165)
            with open(变量720, 'r+b') as 构建915:
                构建915.seek(关闭794)
                构建915.write(结果1122)
            with open(变量720, 'rb') as 构建915:
                构建915.seek(关闭794)
                if 构建915.read(len(结果1122)) != 结果1122:
                    shutil.copy2(计数1165, 变量720)
                    return (False, 'write verification failed', 句柄816)
        句柄816['patched_at'] = '0x%x' % 关闭794
        return (True, 'patched at 0x%x' % 关闭794, 句柄816)
    except Exception as 修补958:
        return (False, 节点57(str(修补958), 60), 句柄816)

def 步骤658(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    键743, 键1383 = 条目573(args.input)
    if 键743 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    报告839 = 打开273(键743, None)
    值1302 = [修补958 for 修补958 in 报告839 if 修补958.name == 'libflutter.so']
    if not 值1302:
        键63.bad('no libflutter.so · this archive does not look like flutter')
        return 3
    键63.head('flutter engine', 字节27)
    for 修补958 in 值1302:
        键63.kv(修补958.name, '%s · %d-bit · %s' % (修补958.machine, 修补958.bits, 表104(修补958.size)), width=22)
        句柄816, 名字709 = 句柄656(修补958.path)
        if 句柄816 is None:
            键63.warn('anchors not resolved · ' + 名字709)
            continue
        键63.kv('anchors', ', '.join(('%s x%d' % (名字989, 步骤818) for 名字989, 步骤818 in 句柄816['anchors'].items())), width=22)
        字节1547 = [映射1132 for 映射1132 in 句柄816['candidates'] if 映射1132['method'] == 'string-pair']
        句柄1456 = [映射1132 for 映射1132 in 句柄816['candidates'] if 映射1132['method'] == 'already-patched']
        if 句柄1456:
            键63.ok('already patched at ' + 句柄1456[0]['start'])
        键63.kv('candidates', '%d paired · %d single' % (len(字节1547), len(句柄816['candidates']) - len(字节1547) - len(句柄1456)), width=22)
        for 映射1132 in 句柄816['candidates'][:4]:
            键63.bullet('%s · ref %s · start %s' % (映射1132['method'], 映射1132['ref'], 映射1132['start']))
        if args.dry_run:
            continue
        ok, 结果922, 读取1112 = 节点657(修补958.path)
        if ok:
            键63.ok('patched · ' + 结果922)
        else:
            键63.bad('patch failed · ' + 结果922)
    if args.dry_run:
        键63.head('dry run', 字节27)
        键63.info('nothing written')
        return 0
    文本708 = Path(args.output).expanduser() if args.output else 映射572(键743, 'flutter')
    try:
        with zipfile.ZipFile(键743) as 名字1429, zipfile.ZipFile(文本708, 'w') as 检查1430:
            for 区块1415 in 名字1429.infolist():
                行1705 = 区块1415.filename.upper()
                if 行1705.startswith('META-INF/') and 行1705.endswith(('.SF', '.RSA', '.DSA', '.EC', '.MF')):
                    continue
                参数761 = 名字1429.read(区块1415.filename)
                for 修补958 in 值1302:
                    if 区块1415.filename.endswith('/' + 修补958.name):
                        参数761 = Path(修补958.path).read_bytes()
                        break
                状态1609 = zipfile.ZipInfo(区块1415.filename, date_time=区块1415.date_time)
                状态1609.compress_type = zipfile.ZIP_STORED if 区块1415.filename.endswith('.so') else 区块1415.compress_type
                状态1609.external_attr = 区块1415.external_attr
                状态1609.internal_attr = 区块1415.internal_attr
                状态1609.create_system = 区块1415.create_system
                检查1430.writestr(状态1609, 参数761)
    except Exception as 修补958:
        键63.bad('repack failed · ' + 节点57(str(修补958), 70))
        return 6
    缓存203({'zipalign': 字节107('zipalign')}, 文本708, 文本708.parent)
    if not args.unsigned:
        源1500, 目标1501 = 路径206(构建195(文本708.parent, allow_net=False, 缓存723=True), 文本708, 文本708.parent, args.password)
        键63.kv('signed', 目标1501 if 源1500 else 'no signer available')
    键63.head('result', 文本28)
    键63.kv('output', str(文本708))
    键63.info('flutter ignores the system proxy · use iptables or a vpn based capture')
    步骤298(文本708)
    return 0

def 栈659(区块895, 句柄896=True):
    列866 = len(区块895)
    键1303 = []
    表744 = bytearray()
    for 节点697 in 区块895:
        节点697 = 节点697 if isinstance(节点697, str) else str(节点697)
        键1303.append(len(表744))
        字节747 = 节点697.encode('utf-8', 'surrogatepass')
        文本1548 = 节点697.encode('utf-16-le', 'surrogatepass')
        表744 += 节点257(len(文本1548) // 2)
        表744 += 节点257(len(字节747))
        表744 += 字节747
        表744 += b'\x00'
    while len(表744) % 4:
        表744 += b'\x00'
    表1304 = 28
    行1305 = 表1304 + 4 * 列866
    total = 行1305 + len(表744)
    表1024 = 256 if 句柄896 else 0
    文本708 = struct.pack('<HHIIIIII', 1, 表1304, total, 列866, 0, 表1024, 行1305, 0)
    文本708 += b''.join((struct.pack('<I', 列786) for 列786 in 键1303))
    文本708 += bytes(表744)
    return 文本708

def 源660(参数721):
    if len(参数721) < 12 or 区块255(参数721, 0) != 2:
        return None
    行745 = 区块255(参数721, 2)
    if 行745 + 8 > len(参数721) or 区块255(参数721, 行745) != 1:
        return None
    return (行745, 句柄256(参数721, 行745 + 4), 栈259(参数721, 行745))

def 目标661(参数721, 节点897, 标记730):
    句柄816 = 源660(参数721)
    if not 句柄816:
        raise ValueError('no global string pool')
    行745, 关闭914, 表984 = 句柄816
    区块895 = list(表984.items)
    if 节点897 < 0 or 节点897 >= len(区块895):
        raise ValueError('string index %d out of range (%d entries)' % (节点897, len(区块895)))
    区块895[节点897] = 标记730
    列1306 = 栈659(区块895)
    文本708 = bytearray(bytes(参数721[:行745]) + 列1306 + bytes(参数721[行745 + 关闭914:]))
    struct.pack_into('<I', 文本708, 4, len(文本708))
    return bytes(文本708)

def 值662(参数721):
    句柄816 = 源660(参数721)
    if not 句柄816:
        return []
    文本708 = []
    行745 = 区块255(参数721, 2)
    end = min(len(参数721), 句柄256(参数721, 4))
    while 行745 + 8 <= end:
        写入1351 = 区块255(参数721, 行745)
        读取1352 = 句柄256(参数721, 行745 + 4)
        if 读取1352 < 8:
            break
        if 写入1351 == 512:
            文本708.extend(键663(参数721, 行745, 读取1352))
        行745 += 读取1352
    return 文本708

def 键663(参数721, 步骤898, 栈899):
    打开913 = 区块255(参数721, 步骤898 + 2)
    字节1307 = 句柄256(参数721, 步骤898 + 268)
    文本1308 = 句柄256(参数721, 步骤898 + 276)
    名字1309 = 栈259(参数721, 步骤898 + 字节1307) if 字节1307 else None
    检查1310 = 栈259(参数721, 步骤898 + 文本1308) if 文本1308 else None
    if not 名字1309 or not 检查1310:
        return []
    文本708 = []
    写入1311 = 步骤898 + 打开913
    end = 步骤898 + 栈899
    列986 = 0
    while 写入1311 + 8 <= end and 列986 < 50000:
        列986 += 1
        写入1351 = 区块255(参数721, 写入1311)
        名字1549 = 区块255(参数721, 写入1311 + 2)
        读取1352 = 句柄256(参数721, 写入1311 + 4)
        if 读取1352 < 8:
            break
        if 写入1351 == 513:
            字节1667 = 参数721[写入1311 + 8]
            列866 = 句柄256(参数721, 写入1311 + 12)
            文本1668 = 句柄256(参数721, 写入1311 + 16)
            名字1669 = 名字1309.get(字节1667 - 1) or 'type%d' % 字节1667
            检查1670 = 写入1311 + 名字1549
            列表847 = 写入1311 + 文本1668
            for 读取912 in range(min(列866, 200000)):
                队列1731 = 句柄256(参数721, 检查1670 + 读取912 * 4)
                if 队列1731 == 4294967295:
                    continue
                映射1732 = 列表847 + 队列1731
                if 映射1732 + 8 > len(参数721):
                    continue
                条目1733 = 区块255(参数721, 映射1732)
                偏移1734 = 区块255(参数721, 映射1732 + 2)
                区块1735 = 句柄256(参数721, 映射1732 + 4)
                name = 检查1310.get(区块1735) or 'entry%d' % 读取912
                if 偏移1734 & 1:
                    文本708.append({'type': 名字1669, 'name': name, 'kind': 'complex', 'value_index': None, 'offset': 映射1732, 'type_id': 字节1667, 'index': 读取912})
                    continue
                句柄1736 = 映射1732 + 条目1733
                if 句柄1736 + 8 > len(参数721):
                    continue
                节点1737 = 参数721[句柄1736 + 3]
                步骤1738 = 句柄256(参数721, 句柄1736 + 4)
                文本708.append({'type': 名字1669, 'name': name, 'kind': 'value', 'value_type': 节点1737, 'value_index': 步骤1738 if 节点1737 == 3 else None, 'raw': 步骤1738, 'offset': 句柄1736, 'type_id': 字节1667, 'index': 读取912})
        写入1311 += 读取1352
    return 文本708

def 表664(参数721):
    if len(参数721) < 12 or 区块255(参数721, 0) != 3:
        return None
    行745 = 区块255(参数721, 2)
    end = min(len(参数721), 句柄256(参数721, 4))
    列986 = 0
    while 行745 + 8 <= end and 列986 < 10000:
        列986 += 1
        if 区块255(参数721, 行745) == 1:
            return (行745, 句柄256(参数721, 行745 + 4))
        读取1352 = 句柄256(参数721, 行745 + 4)
        if 读取1352 < 8:
            break
        行745 += 读取1352
    return None

def 行665(参数721, 源900, 目标901):
    读取1312 = 表664(参数721)
    if not 读取1312:
        return (None, 0)
    行745, 关闭914 = 读取1312
    表984 = 栈259(参数721, 行745)
    区块895 = list(表984.items)
    步骤978 = 0
    for 读取912, 区块1415 in enumerate(区块895):
        if 区块1415 == 源900:
            区块895[读取912] = 目标901
            步骤978 += 1
    if not 步骤978:
        return (None, 0)
    打开1313 = 栈659(区块895)
    文本708 = bytearray(bytes(参数721[:行745]) + 打开1313 + bytes(参数721[行745 + 关闭914:]))
    struct.pack_into('<I', 文本708, 4, len(文本708))
    return (bytes(文本708), 步骤978)

def 列666(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    路径1206 = Path(tempfile.mkdtemp())
    状态729, 字节1107, 键1383 = 句柄616(args.input, 路径1206)
    if 字节1107:
        键63.info(字节1107)
    if 状态729 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    写入751 = Path(tempfile.mkdtemp())
    try:
        键743 = None
        参数721 = None
        if zipfile.is_zipfile(状态729):
            with zipfile.ZipFile(状态729) as 键1023:
                if 'resources.arsc' not in 键1023.namelist():
                    键63.bad('no resources.arsc in this archive')
                    return 3
                参数721 = 键1023.read('resources.arsc')
            键743 = 状态729
        else:
            参数721 = 状态729.read_bytes()
        区块855 = 值662(参数721)
        if not 区块855:
            键63.bad('resources.arsc could not be parsed')
            return 3
        键63.head('resource table', 行25)
        键63.kv('entries', len(区块855), width=18)
        报告1279 = {}
        for 修补958 in 区块855:
            报告1279[修补958['type']] = 报告1279.get(修补958['type'], 0) + 1
        for 名字989, 步骤818 in sorted(报告1279.items(), key=lambda kv: -kv[1])[:10]:
            键63.kv(名字989, 步骤818, width=18)
        if args.arsc_list:
            条目893 = args.arsc_list.lower()
            步骤978 = [修补958 for 修补958 in 区块855 if 条目893 in (修补958['type'] + '/' + 修补958['name']).lower()]
            键63.head('matches', 文本28)
            表984 = 源660(参数721)[2]
            for 修补958 in 步骤978[:60]:
                偏移1414 = ''
                if 修补958.get('value_index') is not None:
                    偏移1414 = 表984.get(修补958['value_index']) or ''
                键63.bullet('%s/%s = %s' % (修补958['type'], 修补958['name'], 节点57(偏移1414, 60) or '<complex>'))
            if not 步骤978:
                键63.info('no entry matched')
            return 0
        if not args.arsc_set:
            键63.info('use --arsc-list NAME to search, --arsc-set type/name=value to change')
            return 0
        表984 = 源660(参数721)[2]
        键1103 = 0
        检查1550 = 参数721
        for 打开1193 in args.arsc_set:
            if '=' not in 打开1193 or '/' not in 打开1193.split('=', 1)[0]:
                键63.warn('bad spec · ' + 节点57(打开1193, 40))
                continue
            变量720, 标记730 = 打开1193.split('=', 1)
            名字1669, 栈1739 = 变量720.split('/', 1)
            数据1288 = [修补958 for 修补958 in 区块855 if 修补958['type'] == 名字1669 and 修补958['name'] == 栈1739]
            if not 数据1288:
                键63.warn('not found · ' + 变量720)
                continue
            读取872 = 数据1288[0]
            if 读取872.get('value_index') is None:
                键63.warn('not a string resource · ' + 变量720)
                continue
            源900 = 表984.get(读取872['value_index']) or ''
            检查1550 = 目标661(检查1550, 读取872['value_index'], 标记730)
            键63.ok('%s/%s · %s -> %s' % (名字1669, 栈1739, 节点57(源900, 24), 节点57(标记730, 24)))
            键1103 += 1
        if not 键1103:
            键63.bad('nothing changed')
            return 5
        check = 值262(检查1550)
        if not check.valid:
            键63.bad('rebuilt table failed to parse · aborted')
            return 6
        if 键743 is None:
            dest = Path(args.output).expanduser() if args.output else 状态729.with_suffix('.patched.arsc')
            行105(dest, 检查1550, 'wb')
            键63.kv('written', str(dest))
            return 0
        dest = Path(args.output).expanduser() if args.output else 映射572(键743, 'res')
        名字669(键743, dest, {'resources.arsc': 检查1550}, args)
        键63.head('result', 文本28)
        键63.kv('changed', 键1103, width=18)
        键63.kv('output', str(dest))
        return 0
    finally:
        shutil.rmtree(写入751, ignore_errors=True)

def 字节667(键743):
    关闭1314 = []
    try:
        with zipfile.ZipFile(键743) as 键1023:
            值1422 = [键1023.read(步骤698) for 步骤698 in 键1023.namelist() if re.match('classes\\d*\\.dex$', 步骤698)]
    except Exception:
        return 关闭1314
    构建1315 = 0
    解析1316 = 0
    计数1285 = 0
    扫描1317 = {}
    for key, 修补718 in 行585.items():
        if 'signature' in 修补718 or 'certificate' in 修补718:
            扫描1317[key] = 'signature'
        elif 修补718 in ('hashes something', 'checksums something'):
            扫描1317[key] = 'integrity'
    for key, 标记730 in 表584.items():
        if 标记730[0] == 'terminate':
            扫描1317[key] = 'exit'
    源820 = time.time() + 25
    for 表744 in 值1422[:3]:
        if time.time() > 源820:
            结果82('survival scan stopped at its time budget')
            break
        try:
            句柄816 = 文本588(表744, 扫描1317, 路径846=8000, 缓存883=源820)
        except Exception:
            continue
        for 写入1551 in 句柄816:
            行705 = 写入1551.get('kind')
            if 行705 == 'exit':
                解析1316 += 1
            elif 行705 == 'signature':
                构建1315 += 1
            elif 行705 == 'integrity':
                计数1285 += 1
    if 构建1315:
        关闭1314.append(('signature', 构建1315, 'the app reads its own signature · a new key will make it exit'))
    if 解析1316:
        关闭1314.append(('exit', 解析1316, 'the app calls System.exit or killProcess · it can close itself on purpose'))
    if 计数1285:
        关闭1314.append(('integrity', 计数1285, 'the app hashes itself · any change to the dex or apk is detectable'))
    return 关闭1314

def 文本668(键743, 键783=None):
    关闭1314 = 字节667(键743)
    if not 关闭1314:
        return
    键63.head('will it survive', 字节27)
    for code, 列866, 字节1467 in 关闭1314:
        键63.warn('%s · %d site(s) · %s' % (code, 列866, 字节1467))
    键63.info('the build is valid, but this app may close on launch')
    键63.info('run: arpxtool %s exit-check' % Path(键743).name)
    键63.info('then: arpxtool %s crashinject' % (Path(键783).name if 键783 else Path(键743).name))

def 名字669(状态729, dest, 值902, args, 键903=()):
    结果82('repack %s -> %s (%d replacement(s))' % (Path(状态729).name, Path(dest).name, len(值902)))
    try:
        with zipfile.ZipFile(状态729) as 名字1429, zipfile.ZipFile(dest, 'w') as 检查1430:
            for 区块1415 in 名字1429.infolist():
                行1705 = 区块1415.filename.upper()
                if 行1705.startswith('META-INF/') and 行1705.endswith(('.SF', '.RSA', '.DSA', '.EC', '.MF')):
                    continue
                参数761 = 值902.get(区块1415.filename)
                if 参数761 is None:
                    参数761 = 名字1429.read(区块1415.filename)
                状态1609 = zipfile.ZipInfo(区块1415.filename, date_time=区块1415.date_time)
                源1740 = 区块1415.filename.endswith('.so') or 区块1415.filename in 键903
                状态1609.compress_type = zipfile.ZIP_STORED if 源1740 else 区块1415.compress_type
                状态1609.external_attr = 区块1415.external_attr
                状态1609.internal_attr = 区块1415.internal_attr
                状态1609.create_system = 区块1415.create_system
                检查1430.writestr(状态1609, 参数761)
            for name, 参数761 in 值902.items():
                if name in {读取912.filename for 读取912 in 名字1429.infolist()}:
                    continue
                状态1609 = zipfile.ZipInfo(name)
                状态1609.compress_type = zipfile.ZIP_STORED if name.endswith('.so') else zipfile.ZIP_DEFLATED
                检查1430.writestr(状态1609, 参数761)
    except Exception as 修补958:
        键63.bad('repack failed · ' + 节点57(str(修补958), 70))
        return False
    条目293(dest)
    if not getattr(args, 'unsigned', False):
        扫描757 = 构建195(dest.parent, allow_net=False, 缓存723=True)
        ok, 目标1501 = 路径206(扫描757, dest, dest.parent, getattr(args, '缓存763', 'arpxtool'))
        键63.kv('signed', 目标1501 if ok else 'no signer available')
    if not 条目613(状态729, dest, 'repack'):
        return False
    文本668(dest, 状态729)
    return True
检查670 = {'google_api_key': b'AIza[0-9A-Za-z_\\-]{35}', 'aws_access_key': b'(?:AKIA|ASIA|AROA|AIDA)[A-Z0-9]{16}', 'google_oauth': b'[0-9]+-[0-9a-z_]{20,}\\.apps\\.googleusercontent\\.com', 'firebase_db': b'[a-z0-9.\\-]+\\.firebaseio\\.com', 'gcp_appspot': b'[a-z0-9.\\-]+\\.appspot\\.com', 'private_key': b'-----BEGIN (?:RSA |EC )?PRIVATE KEY-----', 'jwt': b'eyJ[A-Za-z0-9_\\-]{8,}\\.eyJ[A-Za-z0-9_\\-]{8,}\\.[A-Za-z0-9_\\-]{8,}', 'slack_token': b'xox[baprs]-[0-9A-Za-z\\-]{10,}', 'stripe_key': b'(?:sk|pk)_(?:live|test)_[0-9A-Za-z]{16,}', 'github_token': b'gh[pousr]_[0-9A-Za-z]{36,}', 'sendgrid': b'SG\\.[0-9A-Za-z_\\-]{22}\\.[0-9A-Za-z_\\-]{43}', 'twilio': b'SK[0-9a-fA-F]{32}', 'mapbox': b'pk\\.[0-9A-Za-z]{60,}', 'azure_key': b'AccountKey=[A-Za-z0-9+/=]{40,}'}
写入671 = b"https?://[A-Za-z0-9._~:/?#@!$&'()*+,;=%\\-]{6,}"
读取672 = ('.dex', '.json', '.js', '.xml', '.properties', '.txt', '.cfg', '.html', '.yml', '.yaml', '.env', '.pem', '.key')

def 打开673(变量720):
    检查830 = {}
    状态1129 = set()
    try:
        with zipfile.ZipFile(变量720) as 键1023:
            数据728 = 键1023.namelist()
            for name in 数据728:
                关闭1074 = name.lower()
                if not (关闭1074.endswith(读取672) or 关闭1074.startswith('assets/') or 关闭1074.startswith('res/raw/') or (关闭1074 == 'androidmanifest.xml')):
                    continue
                try:
                    表744 = 键1023.read(name)
                except Exception:
                    continue
                for 修补718, 路径1046 in 检查670.items():
                    for 句柄776 in re.finditer(路径1046, 表744):
                        检查830.setdefault(修补718, []).append((name, 句柄776.group(0)[:120]))
                for 句柄776 in re.finditer(写入671, 表744):
                    状态1129.add(句柄776.group(0)[:160].decode('latin-1'))
    except Exception as 修补958:
        return (None, None, 节点57(str(修补958), 60))
    return (检查830, 状态1129, None)

def 关闭674(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    路径1206 = Path(tempfile.mkdtemp())
    状态729, 字节1107, 键1383 = 句柄616(args.input, 路径1206)
    if 字节1107:
        键63.info(字节1107)
    if 状态729 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    检查830, 状态1129, 名字709 = 打开673(状态729)
    if 名字709:
        键63.bad(名字709)
        return 3
    键63.head('secret scan', 行25)
    total = 0
    for 修补718 in sorted(检查830):
        步骤978 = 检查830[修补718]
        total += len(步骤978)
        键63.kv(修补718, '%d hit(s)' % len(步骤978), width=20)
        句柄1096 = set()
        for 扫描1477, 偏移1414 in 步骤978:
            key = (修补718, 偏移1414)
            if key in 句柄1096:
                continue
            句柄1096.add(key)
            print('    ' + 打开33('%s · %s' % (节点57(扫描1477, 34), 节点57(偏移1414, 54))))
            if len(句柄1096) >= 4:
                break
    键63.head('endpoints', 文本28)
    键63.kv('urls', len(状态1129), width=20)
    for 修补1318 in sorted(状态1129)[:25]:
        print('    ' + 打开33(节点57(修补1318, 88)))
    键63.head('verdict', 字节27 if total else 文本28)
    键63.kv('findings', total, width=20)
    if args.output:
        参数761 = {'findings': {名字989: 步骤818 for 名字989, 步骤818 in 检查830.items()}, 'urls': sorted(状态1129)}
        行105(Path(args.output).expanduser(), json.dumps(参数761, indent=2), 'w')
        键63.kv('written', str(args.output))
    return 0 if not total else 0

def 构建675(args):
    缓存3.probe()
    状态729, 键1383 = 条目573(args.input)
    if 状态729 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    参数721 = None
    if zipfile.is_zipfile(状态729):
        with zipfile.ZipFile(状态729) as 键1023:
            name = args.xml_path or 'AndroidManifest.xml'
            if name not in 键1023.namelist():
                键63.bad('entry not found · ' + name)
                return 3
            参数721 = 键1023.read(name)
    else:
        参数721 = 状态729.read_bytes()
    表904 = 报告279(参数721)
    if not 表904.valid:
        键63.bad('not a binary xml document')
        return 3
    文本708 = 解析676(表904)
    dest = Path(args.output).expanduser() if args.output else 状态729.with_suffix('.xml')
    行105(dest, 文本708.encode('utf-8'), 'wb')
    键63.ok('decoded %d element(s)' % len(表904.elements))
    键63.kv('written', str(dest))
    return 0

def 解析676(表904):
    值702 = ['<?xml version="1.0" encoding="utf-8"?>']
    打开993 = 0
    for 状态929 in 表904.walk:
        if 状态929['kind'] == 'start':
            偏移734 = ''.join((' %s="%s"' % (名字989, 步骤818) for 名字989, 步骤818 in 状态929['attrs']))
            值702.append('%s<%s%s>' % ('  ' * 打开993, 状态929['name'], 偏移734))
            打开993 += 1
        elif 状态929['kind'] == 'end':
            打开993 = max(0, 打开993 - 1)
            值702.append('%s</%s>' % ('  ' * 打开993, 状态929['name']))
    return '\n'.join(值702) + '\n'

def 扫描677(args):
    缓存3.probe()
    状态729, 键1383 = 条目573(args.input)
    if 状态729 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    text = 状态729.read_text(encoding='utf-8', errors='replace')
    try:
        表744 = 列表687(text)
    except Exception as 修补958:
        键63.bad('compile failed · ' + 节点57(str(修补958), 70))
        return 3
    dest = Path(args.output).expanduser() if args.output else 状态729.with_suffix('.binxml')
    行105(dest, 表744, 'wb')
    键63.ok('compiled %d bytes' % len(表744))
    键63.kv('written', str(dest))
    return 0

def 修补678(args):
    缓存3.probe()
    状态729, 键1383 = 条目573(args.input)
    if 状态729 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    参数721 = bytearray(状态729.read_bytes())
    if args.hex_find:
        条目893 = bytes.fromhex(args.hex_find.replace(' ', ''))
        步骤978 = 数据648(bytes(参数721), 条目893)
        键63.head('matches', 文本28)
        键63.kv('pattern', 条目893.hex(), width=18)
        键63.kv('hits', len(步骤978), width=18)
        for 解析956 in 步骤978[:40]:
            键63.bullet('0x%x' % 解析956)
        return 0
    if args.hex_patch:
        for 打开1193 in args.hex_patch:
            if '=' not in 打开1193:
                键63.warn('bad spec · ' + 节点57(打开1193, 30))
                continue
            扫描1477, 偏移1414 = 打开1193.split('=', 1)
            行745 = int(扫描1477, 0)
            表744 = bytes.fromhex(偏移1414.replace(' ', ''))
            if 行745 < 0 or 行745 + len(表744) > len(参数721):
                键63.warn('out of range · 0x%x' % 行745)
                continue
            源900 = bytes(参数721[行745:行745 + len(表744)])
            参数721[行745:行745 + len(表744)] = 表744
            键63.ok('0x%x · %s -> %s' % (行745, 源900.hex(), 表744.hex()))
        dest = Path(args.output).expanduser() if args.output else 映射572(状态729, 'hex')
        行105(dest, bytes(参数721), 'wb')
        键63.kv('written', str(dest))
        return 0
    键63.head('hex', 行25)
    键63.kv('size', 表104(len(参数721)), width=14)
    for 行745 in range(0, min(len(参数721), 512), 16):
        行1345 = bytes(参数721[行745:行745 + 16])
        text = ''.join((chr(映射692) if 32 <= 映射692 < 127 else '.' for 映射692 in 行1345))
        print('  ' + 打开33('%08x  %-47s  %s' % (行745, 行1345.hex(' '), text)))
    return 0

def 报告679(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    状态729, 键1383 = 条目573(args.input)
    if 状态729 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    if not args.clone_pkg:
        键63.bad('--clone-pkg new.package.name is required')
        return 2
    报告1319 = None
    with zipfile.ZipFile(状态729) as 键1023:
        索引884 = 区块615(键1023)[1]
    if 索引884 and 索引884.get('package'):
        报告1319 = 索引884['package']
    if not 报告1319:
        键63.bad('could not read the current package name')
        return 3
    变量1320 = args.clone_pkg
    键63.head('clone', 行25)
    键63.kv('from', 报告1319, width=14)
    键63.kv('to', 变量1320, width=14)
    值902 = {}
    with zipfile.ZipFile(状态729) as 键1023:
        数据728 = 键1023.namelist()
        字节747, 值1662 = 区块615(状态729)
        源1620, 步骤978 = 行665(字节747, 报告1319, 变量1320)
        if not 源1620:
            键63.warn('manifest package could not be rewritten')
        else:
            值902['AndroidManifest.xml'] = 源1620
            键63.ok('manifest package rewritten · %d reference(s)' % 步骤978)
        读取1552 = 报告1319.replace('.', '/')
        打开1553 = 变量1320.replace('.', '/')
        for 步骤698 in 数据728:
            if re.match('classes\\d*\\.dex$', 步骤698):
                表744 = 键1023.read(步骤698)
                目标1741 = 变量680(表744, 报告1319.encode(), 变量1320.encode())
                目标1741 = 变量680(目标1741, 读取1552.encode(), 打开1553.encode())
                if 目标1741 != 表744:
                    值902[步骤698] = 目标1741
                    键63.ok('rewrote ' + 步骤698)
    dest = Path(args.output).expanduser() if args.output else 映射572(状态729, 'clone')
    名字669(状态729, dest, 值902, args)
    键63.head('result', 文本28)
    键63.kv('output', str(dest))
    return 0

def 变量680(参数721, 源900, 目标901):
    if len(源900) != len(目标901):
        return 参数721
    return 参数721.replace(源900, 目标901)

def 参数681(args):
    缓存3.probe()
    列1106 = Path(tempfile.mkdtemp())
    队列691, 报告1439, 变量1440 = 句柄616(args.input, 列1106)
    if 队列691 is None:
        键63.bad('input not found · ' + str(args.input))
        return 2
    if not args.compare_to:
        键63.bad('--compare-to second.apk is required')
        return 2
    映射692, 参数1441, 结果1442 = 句柄616(args.compare_to, 列1106)
    if 映射692 is None:
        键63.bad('second input not found · ' + str(args.compare_to))
        return 2
    for 字节1107 in (报告1439, 参数1441):
        if 字节1107:
            键63.info(字节1107)

    def classes_of(变量720):
        文本708 = {}
        变量720, 写入1671 = 步骤618(变量720, 列1106)
        with zipfile.ZipFile(变量720) as 键1023:
            for 步骤698 in 键1023.namelist():
                if re.match('classes\\d*\\.dex$', 步骤698):
                    for name in 路径686(键1023.read(步骤698)):
                        文本708[name] = 步骤698
        return 文本708
    关闭1554, 构建1555 = (classes_of(队列691), classes_of(映射692))
    字节987 = sorted(set(构建1555) - set(关闭1554))
    句柄1056 = sorted(set(关闭1554) - set(构建1555))
    键63.head('dex compare', 行25)
    键63.kv('left', len(关闭1554), width=14)
    键63.kv('right', len(构建1555), width=14)
    键63.kv('added', len(字节987), width=14)
    键63.kv('removed', len(句柄1056), width=14)
    for 修补718, 区块895, 写入791 in (('added', 字节987, 关闭34), ('removed', 句柄1056, 解析36)):
        if not 区块895:
            continue
        键63.head(修补718, 文本28 if 修补718 == 'added' else 字节27)
        for name in 区块895[:40]:
            print('  ' + 写入791('+ ' if 修补718 == 'added' else '- ') + 打开33(节点57(name, 80)))
        if len(区块895) > 40:
            键63.info('%d more' % (len(区块895) - 40))
    return 0

def 结果682(args):
    缓存3.probe()
    状态729, 键1383 = 条目573(args.input)
    if 状态729 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    参数721 = 状态729.read_bytes()
    结果1042 = 缓存683(参数721)
    键63.head('vdex / oat', 行25)
    键63.kv('input', 状态729.name, width=14)
    键63.kv('size', 表104(len(参数721)), width=14)
    键63.kv('dex payloads', len(结果1042), width=14)
    if not 结果1042:
        键63.warn('no dex payload found')
        return 3
    节点817 = Path(args.output).expanduser() if args.output else 状态729.parent / (状态729.stem + '_dex')
    节点817.mkdir(parents=True, exist_ok=True)
    for 读取912, 表744 in enumerate(结果1042):
        dest = 节点817 / ('classes%s.dex' % ('' if 读取912 == 0 else str(读取912 + 1)))
        行105(dest, 表744, 'wb')
        区块815 = 写入311(表744)
        键63.ok('%s · %s · %d class(es)' % (dest.name, 表104(len(表744)), 区块815.c_n if 区块815.ok else 0))
    键63.kv('written', str(节点817))
    return 0

def 缓存683(参数721):
    文本708 = []
    for 参数1321 in (b'035', b'036', b'037', b'038', b'039', b'040', b'041'):
        条目893 = b'dex\n' + 参数1321 + b'\x00'
        start = 0
        while True:
            读取912 = 参数721.find(条目893, start)
            if 读取912 < 0:
                break
            if 读取912 + 112 <= len(参数721):
                关闭914 = 句柄256(参数721, 读取912 + 32)
                if 112 < 关闭914 <= len(参数721) - 读取912:
                    表744 = 参数721[读取912:读取912 + 关闭914]
                    区块815 = 写入311(表744)
                    if 区块815.ok:
                        文本708.append(表744)
                        start = 读取912 + 关闭914
                        continue
            start = 读取912 + 4
    return 文本708

def 索引684(args):
    缓存3.probe()
    计数5.reset()
    if not args.quiet:
        节点97(not 缓存3.enabled)
    if not 句柄536(['reapk'], 'dex assembly'):
        键63.bad('reapk is required for smali level editing · pip install reapk')
        return 3
    import reapk as _reapk
    状态729, 键1383 = 条目573(args.input)
    if 状态729 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    if not args.dex_show and (not args.dex_set):
        键63.bad('use --dex-show Class;->method()Z or --dex-set ...=file.smali')
        return 2
    with zipfile.ZipFile(状态729) as 键1023:
        变量1360 = [步骤698 for 步骤698 in 键1023.namelist() if re.match('classes\\d*\\.dex$', 步骤698)]
        if not 变量1360:
            键63.bad('no dex in this archive')
            return 3
        解析1556 = {步骤698: 键1023.read(步骤698) for 步骤698 in 变量1360}
    关闭794 = None
    for name, 表744 in 解析1556.items():
        try:
            行785 = _reapk.DexFile(表744)
            for cls in 行785.classes():
                for 句柄776 in 行785.class_methods(cls['cdata']):
                    if 句柄776.get('code_off'):
                        关闭794 = 关闭794 or (name, 表744, 行785, cls, 句柄776)
        except Exception:
            continue
    if not 关闭794:
        键63.bad('no method with code found')
        return 3
    键63.head('dex', 行25)
    for name, 表744 in 解析1556.items():
        区块815 = 写入311(表744)
        键63.kv(name, '%s · %d class(es)' % (表104(len(表744)), 区块815.c_n if 区块815.ok else 0), width=14)
    if args.dex_show:
        句柄816 = None
        for name, 表744 in 解析1556.items():
            try:
                行785 = _reapk.DexFile(表744)
            except Exception:
                continue
            for cls in 行785.classes():
                if cls['name'] != args.dex_show_class:
                    continue
                for 句柄776 in 行785.class_methods(cls['cdata']):
                    if 句柄776.get('name') == args.dex_show:
                        句柄816 = (name, 表744, 行785, cls, 句柄776)
        if not 句柄816:
            键63.bad('method not found')
            return 3
        name, 表744, 行785, cls, 句柄776 = 句柄816
        映射1652, 值702 = _reapk.disassemble(行785, 句柄776['code_off'])
        键63.head('smali', 文本28)
        键63.kv('registers', 映射1652['regs'], width=14)
        键63.kv('ins', 映射1652['ins'], width=14)
        for 计数885 in 值702:
            print('  ' + 打开33(计数885))
        return 0
    return 0

def 计数685(args):
    缓存3.probe()
    状态729, 键1383 = 条目573(args.input)
    if 状态729 is None:
        键63.bad('input not found · ' + str(args.input))
        for 构建1435 in (键1383 or [])[:5]:
            键63.info('looked in ' + str(构建1435))
        return 2
    if not 句柄536(['reapk'], 'native signing'):
        键63.bad('reapk is required · pip install reapk')
        return 3
    import reapk as _reapk
    字节747 = 状态729.read_bytes()
    try:
        源1500 = _reapk.apk_sign_v2(字节747)
    except Exception as 修补958:
        键63.bad('signing failed · ' + 节点57(str(修补958), 70))
        return 7
    dest = Path(args.output).expanduser() if args.output else 映射572(状态729, 'signed')
    行105(dest, 源1500, 'wb')
    键63.head('native signing', 文本28)
    键63.kv('schemes', 'v2 + v3', width=14)
    键63.kv('input', 表104(len(字节747)), width=14)
    键63.kv('output', 表104(len(源1500)), width=14)
    键63.kv('written', str(dest))
    return 0

def 路径686(参数721):
    区块815 = 写入311(参数721)
    if not 区块815.ok:
        return []
    文本708 = []
    for 读取912 in range(区块815.c_n):
        try:
            读取1672 = 句柄256(参数721, 区块815.c_off + 读取912 * 32)
            name = 区块815.type_name(读取1672)
            if name:
                文本708.append(name)
        except Exception:
            continue
    return 文本708

def 列表687(text):
    import xml.etree.ElementTree as ET
    字节787 = ET.fromstring(text)
    节点737 = []
    值982 = []

    def intern(节点697):
        if 节点697 not in 值982:
            值982.append(节点697)
        return 值982.index(节点697)

    def 表944(name):
        if name.startswith('{'):
            值1742, 读取1112, 列1186 = name[1:].partition('}')
            return 'android:' + 列1186 if 'android' in 值1742 else 列1186
        return name

    def walk(状态929):
        节点737.append(('start', 表944(状态929.tag), [(表944(名字989), 步骤818) for 名字989, 步骤818 in 状态929.attrib.items()]))
        for 写入1311 in 状态929:
            walk(写入1311)
        节点737.append(('end', 表944(状态929.tag), []))
    walk(字节787)
    intern('android')
    for 读取1112, 映射732, 偏移734 in 节点737:
        intern(映射732)
        for 名字989, 步骤818 in 偏移734:
            intern(名字989)
            intern(步骤818)
    表984 = 栈659(值982)
    列表847 = bytearray()
    键983 = []
    for 行705, 映射732, 偏移734 in 节点737:
        if 行705 == 'start':
            文本748 = intern(映射732)
            参数761 = b''
            for 名字989, 步骤818 in 偏移734:
                参数761 += struct.pack('<IIIHBBI', 4294967295, intern(名字989), 4294967295, 8, 0, 3, intern(步骤818))
            区块1015 = struct.pack('<IIHHHHHH', 4294967295, 文本748, 20, 20, len(偏移734), 0, 0, 0)
            关闭914 = 16 + len(区块1015) + len(参数761)
            列表847 += struct.pack('<HHIII', 258, 16, 关闭914, 1, 4294967295) + 区块1015 + 参数761
            键983.append((映射732, 文本748))
        else:
            if not 键983:
                continue
            映射732, 文本748 = 键983.pop()
            列表847 += struct.pack('<HHIIIII', 259, 16, 24, 1, 4294967295, 4294967295, 文本748)
    total = 8 + len(表984) + len(列表847)
    return struct.pack('<HHI', 3, 8, total) + 表984 + bytes(列表847)

def 数据688():
    结果1322 = argparse.ArgumentParser(prog='arpxtool', add_help=True, description='ARPX · Android reverse engineering toolkit')
    结果1322.add_argument('-i', '--input', help='target .apk / .apks / .xapk / .apkm / .zip')
    结果1322.add_argument('-m', '--mode', default=None, choices=sorted(索引244))
    结果1322.add_argument('-o', '--output', help='output apk path')
    结果1322.add_argument('--strategy', default='auto', choices=['auto', 'standard', 'surgical', 'surgery'])
    结果1322.add_argument('--password', default='arp-research', help='keystore password')
    结果1322.add_argument('--keep', action='store_true', help='keep the working tree')
    结果1322.add_argument('--dry', action='store_true', help='analyse patch sites without writing')
    结果1322.add_argument('--no-net', action='store_true', help='never download engines')
    结果1322.add_argument('--no-anim', action='store_true', help='disable animation')
    结果1322.add_argument('--quiet', action='store_true', help='skip the banner')
    结果1322.add_argument('--report', action='store_true', help='write a json report')
    结果1322.add_argument('--copy-download', action='store_true', help='copy result to /sdcard/Download')
    结果1322.add_argument('--unpack', help='extract every archive entry to this directory')
    结果1322.add_argument('--dump', help='write class and string dumps to this directory')
    结果1322.add_argument('--decode', action='store_true', help='also produce a smali tree')
    结果1322.add_argument('--no-report', action='store_true', help='skip the html report')
    结果1322.add_argument('--fast', action='store_true', help='manifest and native only, never touch smali')
    结果1322.add_argument('--engine', help='force an apktool version, e.g. 2.12.1')
    结果1322.add_argument('--flutter-engine', help="drop-in libflutter.so (e.g. reFlutter's patched build)")
    结果1322.add_argument('--remove-license', action='store_true', help='neutralise Play Store licence checks (LVL / PairIP)')
    结果1322.add_argument('--resume', help='rebuild from a preserved work tree')
    结果1322.add_argument('--doctor', action='store_true', help='diagnose the host and the toolchain')
    结果1322.add_argument('--clean', action='store_true', help='purge stale work trees and reclaim space')
    结果1322.add_argument('--compare', help='second archive to diff against --input')
    结果1322.add_argument('--search', help='search a string across dex, native and asset payloads')
    结果1322.add_argument('--cert', action='store_true', help='print signing certificate facts')
    结果1322.add_argument('--batch', help='process every archive under a directory')
    结果1322.add_argument('--log', help='write the session log to this path')
    结果1322.add_argument('--no-log', action='store_true', help='disable the session log')
    结果1322.add_argument('--frida', help='write a frida hook script for detected pinning')
    结果1322.add_argument('--mapping', help='proguard mapping file to deobfuscate names')
    结果1322.add_argument('--java', help='decompile to java sources with jadx into this directory')
    结果1322.add_argument('--disasm', type=int, help='disassemble this many native instructions per object')
    结果1322.add_argument('--targets', help='file listing class#method targets to neutralise')
    结果1322.add_argument('--methods', help='list dex methods matching a regex')
    结果1322.add_argument('--security-test', action='store_true', help='run the defensive security test suite')
    结果1322.add_argument('--rules', help='json or yaml rule file for custom detection')
    结果1322.add_argument('--baseline', help='earlier build to diff findings against')
    结果1322.add_argument('--patch', help='json patch set to apply')
    结果1322.add_argument('--profile', help='patch profile name')
    结果1322.add_argument('--revert', help='journal file to revert from')
    结果1322.add_argument('--force', action='store_true', help='apply despite conflicts or validation failures')
    结果1322.add_argument('--components', action='store_true', help='map ad, license, billing and signature components')
    结果1322.add_argument('--native', action='store_true', help='native object report with JNI and relocations')
    结果1322.add_argument('--strings', type=int, help='how many native strings to print')
    结果1322.add_argument('--ads-manager', action='store_true', help='detect ad sdks and generate a call-site patch set')
    结果1322.add_argument('--license-manager', action='store_true', help='detect license checks and generate a patch set')
    结果1322.add_argument('--billing-manager', action='store_true', help='detect billing usage and generate a patch set')
    结果1322.add_argument('--signature-manager', action='store_true', help='signature dependency and self-check manager')
    结果1322.add_argument('--native-analysis', action='store_true', help='native protection reference report')
    结果1322.add_argument('--apply', action='store_true', help='apply the generated patch set')
    结果1322.add_argument('--dry-run', action='store_true', help='plan only, never write')
    结果1322.add_argument('--native-patch', help='comma separated native symbols to stub in every .so')
    结果1322.add_argument('--max-engines', type=int, default=3, help='how many apktool engines to try (default 3)')
    结果1322.add_argument('--install-check', action='store_true', help='diagnose why an archive would refuse to install')
    结果1322.add_argument('--embed-ca', help='pem certificate to trust inside the network security config')
    结果1322.add_argument('--unsigned', action='store_true', help='skip signing')
    结果1322.add_argument('--keystore', help='custom keystore to sign with')
    结果1322.add_argument('--alias', help='key alias inside the keystore')
    结果1322.add_argument('--store-pass', help='keystore password')
    结果1322.add_argument('--key-pass', help='key password')
    结果1322.add_argument('--v1', action='store_true', help='force v1 signing on')
    结果1322.add_argument('--v2', action='store_true', help='force v2 signing on')
    结果1322.add_argument('--v3', action='store_true', help='force v3 signing on')
    结果1322.add_argument('--no-v1', action='store_true', help='disable v1 signing')
    结果1322.add_argument('--no-v2', action='store_true', help='disable v2 signing')
    结果1322.add_argument('--no-v3', action='store_true', help='disable v3 signing')
    结果1322.add_argument('--menu', action='store_true', help='open the interactive selector')
    结果1322.add_argument('--install-cli', nargs='?', const='arpxtool', help='create a shell launcher, default name arpxtool')
    结果1322.add_argument('--config', help='json file with default settings')
    结果1322.add_argument('--netsec-mode', default='user', choices=sorted(字节147), help='trust anchors written into the network security config')
    结果1322.add_argument('--threads', type=int, help='apktool worker threads')
    结果1322.add_argument('--timeout', type=int, help='per command timeout in seconds')
    结果1322.add_argument('--edit', help='json file of instruction level edits')
    结果1322.add_argument('--ssl-engine', action='store_true', help='deep tls surface discovery and patching')
    结果1322.add_argument('--signature-engine', action='store_true', help='deep signature check discovery and patching')
    结果1322.add_argument('--so-report', action='store_true', help='deep native object report with entropy and markers')
    结果1322.add_argument('--arsc', action='store_true', help='resource table read and write')
    结果1322.add_argument('--arsc-list', metavar='NAME', help='search resource entries by type or name')
    结果1322.add_argument('--arsc-set', action='append', metavar='TYPE/NAME=VALUE', help='change a string resource')
    结果1322.add_argument('--xml-path', help='entry inside the archive to decode')
    结果1322.add_argument('--hex-find', metavar='HEX', help='find a byte pattern')
    结果1322.add_argument('--hex-patch', action='append', metavar='OFF=HEX', help='overwrite bytes at an offset')
    结果1322.add_argument('--clone-pkg', metavar='PKG', help='new package name for a clone')
    结果1322.add_argument('--compare-to', metavar='APK', help='second archive to compare against')
    结果1322.add_argument('--dex-show', metavar='METHOD', help='print the smali of a method')
    结果1322.add_argument('--dex-show-class', metavar='CLASS', help='class for --dex-show')
    结果1322.add_argument('--dex-set', metavar='CLASS;->M=SML', help='replace a method body from a smali file')
    结果1322.add_argument('--secrets', action='store_true', help='scan for api keys, tokens and endpoints')
    结果1322.add_argument('--axml2xml', action='store_true', help='decode binary xml to text')
    结果1322.add_argument('--xml2axml', action='store_true', help='compile text xml to binary')
    结果1322.add_argument('--hex', action='store_true', help='hex view, find or patch')
    结果1322.add_argument('--clone', action='store_true', help='clone the archive under a new package')
    结果1322.add_argument('--compare-dex', action='store_true', help='semantic class level comparison')
    结果1322.add_argument('--vdex', action='store_true', help='extract dex payloads from vdex or oat')
    结果1322.add_argument('--dex-edit', action='store_true', help='smali level editing through reapk')
    结果1322.add_argument('--sign-native', action='store_true', help='sign v2 and v3 without java')
    结果1322.add_argument('--tools', action='store_true', help='inventory of external tools')
    结果1322.add_argument('--install-all', action='store_true', help='install every external tool at once')
    结果1322.add_argument('--provenance', action='store_true', help='show build identity and verify its seal')
    结果1322.add_argument('--repair', action='store_true', help='strip a stale signature block and re-sign')
    结果1322.add_argument('--keygen', action='store_true', help='create a signing keystore')
    结果1322.add_argument('--keygen-app', action='store_true', help='create a keystore named after the app package')
    结果1322.add_argument('--identify', action='store_true', help='show which key signed the archive')
    结果1322.add_argument('--diagnose', action='store_true', help='every reason an install would fail')
    结果1322.add_argument('--exit-check', action='store_true', help='why an app closes right after launch')
    结果1322.add_argument('--crash-read', action='store_true', help='map a stack trace onto the apk')
    结果1322.add_argument('--crash-apk', metavar='APK', help='apk to map crash frames against')
    结果1322.add_argument('--crashpatch', action='store_true', help='set debuggable so crashes print a trace')
    结果1322.add_argument('--axml-info', action='store_true', help='show the chunk layout of the binary manifest')
    结果1322.add_argument('--fix-native', action='store_true', help='store and page align every native library')
    结果1322.add_argument('--crashinject', action='store_true', help='add an in-app crash handler that writes the trace to sdcard')
    结果1322.add_argument('--logcat', action='store_true', help='pull crash and anr data from the device')
    结果1322.add_argument('--package', help='package to filter logcat by')
    结果1322.add_argument('--source', choices=('crash', 'dropbox', 'all'), default='all', help='where to read from')
    结果1322.add_argument('--fix-split', action='store_true', help='clear split flags from the manifest')
    结果1322.add_argument('--sdk', type=int, help='device api level for install checks')
    结果1322.add_argument('--abi', help='device abi, e.g. arm64-v8a')
    结果1322.add_argument('--sign-apk', dest='sign_apk', action='store_true', help='sign with the remembered keystore')
    结果1322.add_argument('--dname', help='certificate subject for keygen')
    结果1322.add_argument('--validity', type=int, help='keystore validity in days')
    结果1322.add_argument('--keysize', type=int, help='rsa key size')
    结果1322.add_argument('--overwrite', action='store_true', help='replace an existing keystore')
    结果1322.add_argument('--flutter-ssl', action='store_true', help='locate and patch the boringssl verifier in libflutter.so')
    结果1322.add_argument('--setup', action='store_true', help='install missing external tools')
    结果1322.add_argument('--yes', action='store_true', help='confirm package installation')
    结果1322.add_argument('--no-install', action='store_true', help='never install tools automatically')
    结果1322.add_argument('--show-commands', action='store_true', help='keep executed command lines visible')
    结果1322.add_argument('--trace', action='store_true', help='print every command and step the tool runs')
    结果1322.add_argument('--exec-detail', action='store_true', help='after each command, print its exit code, time and output')
    结果1322.add_argument('--trace-file', metavar='PATH', help='append the trace to a file')
    结果1322.add_argument('--anim', metavar='STYLE', choices=路径86, help='banner animation style')
    结果1322.add_argument('--logo', choices=('big', 'compact'), help='banner lettering')
    结果1322.add_argument('--sign', action='store_true', help='sign the result after applying')
    结果1322.add_argument('--full-modification', action='store_true', help='run every manager and merge the patch sets')
    结果1322.add_argument('--self-check', action='store_true', help='run internal diagnostics')
    结果1322.add_argument('-v', '--version', action='version', version='%s %s %s' % (写入71, 读取72, 打开73))
    return 结果1322

def 状态689(args):
    缓存3.probe()
    节点97(args.no_anim or not 缓存3.enabled)
    mode = args.mode or 计数245('select operation', [('re', 'REPORT', 'decompile + deep static analysis'), ('unpack', 'UNPACK', 'extract every entry, byte for byte'), ('fast', 'FAST', 'manifest + netsec only, never smali'), ('surgery', 'SURGERY', 'no java, no apktool, no aapt2'), ('signature', 'SIGNATURE', 'neutralise app-level signature checks'), ('detect', 'DETECT', 'ads · billing · license · signature map'), ('full', 'FULL', 'binary + bytecode + manifest + sign'), ('ssl', 'SSL', 'tls verification neutralisation'), ('security', 'SECURITY', 'root · vpn · frida · emulator'), ('native', 'NATIVE', 'binary only, surgical repack'), ('inspect', 'INSPECT', 'read only forensic report'), ('verify', 'VERIFY', 'signature and archive audit')])
    if not mode:
        键63.info('cancelled')
        return 0
    args.mode = mode
    if not args.input:
        print()
        try:
            字节747 = input('  ' + 扫描37(列表47) + ' ' + 修补38('target path: ')).strip().strip('\'"')
        except (EOFError, KeyboardInterrupt):
            return 0
        if not 字节747:
            键63.bad('no input')
            return 1
        args.input = 字节747
    if mode == 'fast':
        args.fast = True
    if mode in ('re', 'unpack'):
        if mode == 'unpack' and (not args.unpack):
            args.unpack = str((条目573(args.input)[0] or Path(args.input)).with_suffix('')) + '_unpack'
            args.decode = True
        return 路径286(args)
    return 路径246(args)

def 标记690(列706=None):
    缓存3.probe()
    字节747 = list(sys.argv[1:] if 列706 is None else 列706)
    扫描1557, action = 关闭474(字节747)
    if action == 'reference':
        return 扫描477()
    if isinstance(action, tuple) and action[0] == 'missing-arg':
        键63.bad("'" + action[1] + "' needs a value")
        return 2
    列706 = 扫描1557
    if 列706 == ['--menu'] or 列706 == []:
        if 列706 == ['--menu']:
            列706 = []
        return 状态689(数据688().parse_args([]))
    args = 数据688().parse_args(列706)
    args = 结果482(args)
    索引204['keystore'] = getattr(args, '扫描877', None)
    索引204['alias'] = getattr(args, '打开873', None)
    索引204['store_pass'] = getattr(args, '行1025', None)
    索引204['key_pass'] = getattr(args, '列1026', None)
    索引204['v1'] = not getattr(args, 'no_v1', False) or getattr(args, 'v1', False)
    索引204['v2'] = not getattr(args, 'no_v2', False) or getattr(args, 'v2', False)
    索引204['v3'] = not getattr(args, 'no_v3', False) or getattr(args, 'v3', False)
    映射532['install'] = not getattr(args, 'no_install', False)
    缓存83['on'] = bool(getattr(args, 'exec_detail', False))
    参数81['on'] = bool(getattr(args, '结果82', False) or getattr(args, 'trace_file', None) or 缓存83['on'])
    参数81['file'] = getattr(args, 'trace_file', None)
    if getattr(args, 'anim', None):
        列表87['style'] = args.anim
    if getattr(args, 'logo', None):
        报告79['big'] = args.logo == 'big'
    if 参数81['on']:
        结果82('arpxtool ' + ' '.join(列706), 'start')
    if not args.no_log:
        表344(args.log)
    if args.self_check:
        return 数据248()
    if args.doctor:
        return 区块215()
    if args.batch:
        return 状态369(args)
    if args.input and args.mode == 'surgery':
        return 结果282(args)
    if args.input and args.mode == 'detect':
        return 计数285(args)
    if args.input and args.security_test:
        return 节点417(args)
    if args.revert or (args.patch and args.input):
        return 文本428(args)
    if args.components and args.input:
        return 缓存443(args)
    if args.native and args.input:
        return 计数445(args)
    if args.ads_manager and args.input:
        return 值462(args, 'ads')
    if args.license_manager and args.input:
        return 值462(args, 'license')
    if args.billing_manager and args.input:
        return 值462(args, 'billing')
    if args.signature_manager and args.input:
        return 值462(args, 'signature')
    if args.native_analysis and args.input:
        return 计数445(args)
    if args.full_modification and args.input:
        return 键463(args)
    if args.native_patch and args.input:
        return 文本468(args)
    if args.install_check and args.input:
        return 栈299(args)
    if args.edit and args.input:
        return 节点497(args)
    if args.ssl_engine and args.input:
        return 写入511(args)
    if args.signature_engine and args.input:
        return 结果522(args)
    if args.so_report and args.input:
        return 数据528(args)
    if args.secrets and args.input:
        return 关闭674(args)
    if args.arsc and args.input:
        return 列666(args)
    if args.axml2xml and args.input:
        return 构建675(args)
    if args.xml2axml and args.input:
        return 扫描677(args)
    if args.hex and args.input:
        return 修补678(args)
    if args.clone and args.input:
        return 报告679(args)
    if args.compare_dex and args.input:
        return 参数681(args)
    if args.vdex and args.input:
        return 结果682(args)
    if args.dex_edit and args.input:
        return 索引684(args)
    if args.sign_native and args.input:
        return 计数685(args)
    if args.flutter_ssl and args.input:
        return 步骤658(args)
    if args.keygen_app and args.input:
        return 构建635(args)
    if args.crash_read and args.input:
        return 参数601(args)
    if args.fix_native and args.input:
        return 字节627(args)
    if args.axml_info and args.input:
        return 表624(args)
    if args.crashinject and args.input:
        return 值622(args)
    if args.crashpatch and args.input:
        return 文本628(args)
    if args.logcat:
        return 结果602(args)
    if args.exit_check and args.input:
        return 检查630(args)
    if args.diagnose and args.input:
        return 写入631(args)
    if args.identify and args.input:
        return 关闭634(args)
    if args.keygen:
        return 扫描637(args)
    if args.sign_apk and args.input:
        return 修补638(args)
    if args.repair and args.input:
        return 报告639(args)
    if args.provenance:
        return 变量640(args)
    if args.install_all:
        return 参数641(args)
    if args.tools:
        return 结果642(args)
    if args.setup:
        return 索引644(args)
    if args.install_cli is not None:
        return 报告479(args)
    if args.clean:
        return 列306()
    if args.compare and args.input:
        return 字节307(args)
    if args.methods and args.input:
        return 数据368(args)
    if args.search and args.input:
        return 文本308(args)
    if args.cert and args.input:
        return 名字309(args)
    try:
        if args.input and args.mode in ('re', 'unpack'):
            if args.mode == 'unpack' and (not args.unpack):
                args.unpack = str((条目573(args.input)[0] or Path(args.input)).with_suffix('')) + '_unpack'
                args.decode = True
            return 路径286(args)
        if args.input and args.mode:
            return 路径246(args)
        return 状态689(args)
    except KeyboardInterrupt:
        print()
        键63.warn('interrupted')
        return 130
    except Exception as 修补958:
        print()
        键63.bad('fatal · ' + 节点57(str(修补958), 120))
        打开1673 = traceback.extract_tb(修补958.__traceback__)
        if 打开1673:
            变量960 = 打开1673[-1]
            键63.info('%s line %d in %s' % (os.path.basename(变量960.filename), 变量960.lineno, 变量960.name))
        if os.environ.get('ARP_DEBUG'):
            raise
        return 1
    finally:
        步骤58.close()
        if 键343['path']:
            print()
            键63.kv('log', str(键343['path']))
        列346()
        if 缓存3.enabled:
            sys.stdout.write(索引4.RESET)
        sys.stdout.flush()
if __name__ == '__main__':
    sys.exit(标记690())
