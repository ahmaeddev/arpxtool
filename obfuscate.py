#!/usr/bin/env python3
"""Turn a python source into an unreadable one — everything renamed.

- every module level name, parameter and local variable becomes a chinese word
- keyword arguments at call sites are rewritten to match the renamed parameters
- string names used by globals()/hasattr()/getattr() are rewritten too
- comments and docstrings are dropped, the tree is unparsed

Imports, builtins and standard-library keyword names are never touched: those
are not ours to rename.
"""
import ast
import builtins
import sys

POOL = ["变量", "参数", "结果", "缓存", "索引", "计数", "路径", "列表", "数据", "状态",
        "标记", "队列", "映射", "条目", "偏移", "区块", "句柄", "节点", "步骤", "栈",
        "源", "目标", "值", "键", "表", "行", "列", "字节", "文本", "名字",
        "检查", "写入", "读取", "打开", "关闭", "构建", "解析", "扫描", "修补", "报告"]

# never rename these: they are keyword names of the standard library, and a
# rename would silently break open(), subprocess.run(), zipfile, argparse...
KEEP_PARAMS = {
    "help", "action", "dest", "required", "choices", "type", "metavar", "nargs",
    "const", "default", "parents", "exist_ok", "timeout", "encoding", "errors",
    "indent", "key", "reverse", "file", "level", "mode", "newline", "flush",
    "check", "shell", "text", "stdout", "stderr", "cwd", "env", "input",
    "capture_output", "universal_newlines", "allow_zip64", "compress_type",
    "date_time", "external_attr", "create_system", "start", "end", "sort_keys",
    "ensure_ascii", "separators", "allow_nan", "name", "args", "kwargs",
    "self", "cls", "sig", "frame", "event", "command", "prompt",
    "needles", "want", "cap", "limit", "dry", "allow_net", "abi", "ret",
}

RESERVED = set(dir(builtins))


class Mapper:
    def __init__(self):
        self.map = {}
        self.module = set()
        self.params = set()
        self.n = 0

    def get(self, name):
        if name in self.map:
            return self.map[name]
        self.n += 1
        new = "%s%d" % (POOL[self.n % len(POOL)], self.n)
        self.map[name] = new
        return new


def _strip_docstrings(node):
    for child in ast.walk(node):
        if isinstance(child, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            body = child.body
            if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                    and isinstance(body[0].value.value, str):
                child.body = body[1:] or [ast.Pass()]
    return node


def collect(tree):
    """One global map: module names, parameters, locals. Same name -> same word."""
    m = Mapper()
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                imported.add((a.asname or a.name).split(".")[0])
        elif isinstance(node, ast.ImportFrom):
            for a in node.names:
                imported.add(a.asname or a.name)

    def add(name, is_param=False):
        if not name or name in imported or name in RESERVED or name.startswith("__"):
            return
        if name in KEEP_PARAMS:
            # a name that is a keyword of some stdlib call stays readable
            # everywhere, otherwise cls/self/name break their call sites
            return
        m.get(name)
        if is_param:
            m.params.add(name)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            add(node.name)
            m.module.add(node.name)
        elif isinstance(node, ast.Assign):
            for t in node.targets:
                if isinstance(t, ast.Name):
                    add(t.id)
                    m.module.add(t.id)
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            add(node.target.id)
        elif isinstance(node, (ast.Try, ast.If, ast.For, ast.While, ast.With)):
            for sub in ast.walk(node):
                if isinstance(sub, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    add(sub.name)
                elif isinstance(sub, ast.Assign):
                    for t in sub.targets:
                        if isinstance(t, ast.Name) and isinstance(sub, ast.Assign):
                            add(t.id)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            a = node.args
            for arg in list(a.posonlyargs) + list(a.args) + list(a.kwonlyargs):
                add(arg.arg, is_param=True)
            if a.vararg:
                add(a.vararg.arg, is_param=True)
            if a.kwarg:
                add(a.kwarg.arg, is_param=True)
        elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Store):
            add(node.id)
        elif isinstance(node, ast.ExceptHandler) and node.name:
            add(node.name)
    # a method or a class attribute is reached as obj.name, and attribute names
    # are left alone — renaming them would desynchronise every self.x call site
    keep = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    keep.add(child.name)
                elif isinstance(child, ast.Assign):
                    for t in child.targets:
                        if isinstance(t, ast.Name):
                            keep.add(t.id)
                elif isinstance(child, ast.AnnAssign) and isinstance(child.target, ast.Name):
                    keep.add(child.target.id)
    for name in keep:
        m.map.pop(name, None)
        m.module.discard(name)
        m.params.discard(name)
    return m


class Rewrite(ast.NodeTransformer):
    def __init__(self, m):
        self.m = m

    def visit_Name(self, node):
        node.id = self.m.map.get(node.id, node.id)
        return node

    def visit_arg(self, node):
        node.arg = self.m.map.get(node.arg, node.arg)
        return node

    def visit_FunctionDef(self, node):
        node.name = self.m.map.get(node.name, node.name)
        self.generic_visit(node)
        return node

    visit_AsyncFunctionDef = visit_FunctionDef

    def visit_ClassDef(self, node):
        node.name = self.m.map.get(node.name, node.name)
        self.generic_visit(node)
        return node

    def visit_ExceptHandler(self, node):
        if node.name:
            node.name = self.m.map.get(node.name, node.name)
        self.generic_visit(node)
        return node

    def visit_keyword(self, node):
        # only a renamed parameter forces a keyword rename; a local variable that
        # happens to share a stdlib keyword name (errors=, timeout=) must not
        if node.arg and node.arg in self.m.params:
            node.arg = self.m.map.get(node.arg, node.arg)
        self.generic_visit(node)
        return node

    def visit_Attribute(self, node):
        # attribute names are api surface (args.flutter_engine, self.width):
        # only the object is rewritten
        node.value = self.visit(node.value)
        return node

    def visit_Call(self, node):
        fn = node.func
        dynamic = isinstance(fn, ast.Name) and fn.id in ("globals", "hasattr", "getattr", "setattr")
        self.generic_visit(node)
        if dynamic:
            for arg in node.args[1:2]:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value in self.m.map:
                    arg.value = self.m.map[arg.value]
        return node


def obfuscate(src, path="<src>", aliases=False):
    tree = ast.parse(src, filename=path)
    tree = _strip_docstrings(tree)
    m = collect(tree)
    tree = Rewrite(m).visit(tree)
    ast.fix_missing_locations(tree)
    out = ast.unparse(tree)
    if aliases:
        lines = ["", "# verification shim"]
        for old in sorted(m.module):
            new = m.map.get(old)
            if new and old.isidentifier() and new.isidentifier():
                lines.append("%s = %s" % (old, new))
        out += "\n".join(lines) + "\n"
    return out + "\n", m


def main():
    argv = [a for a in sys.argv[1:] if a != "--aliases"]
    if len(argv) < 2:
        print("usage: obfuscate.py <in.py> <out.py> [--aliases]")
        return 2
    src = open(argv[0], encoding="utf-8").read()
    out, m = obfuscate(src, argv[0], aliases="--aliases" in sys.argv)
    open(argv[1], "w", encoding="utf-8").write(out)
    print("%s -> %s · %d names renamed · %d -> %d bytes"
          % (argv[0], argv[1], len(m.map), len(src), len(out)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
