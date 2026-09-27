#!/usr/bin/env python3
"""Compare a hub's config with what this version of Pave reads.

    pave-config.py check <config>   report what to fix
    pave-config.py fix <config>     apply the fixes, editing only the lines involved
    pave-config.py count <config>   print how many things there are to fix

The comparison is against what Pave reads now, so it is right however old the
config is. Findings:

  leftover  a key Pave no longer reads, moved to its replacement or removed
  missing   an agent with no entry, running on Pave's default
  invalid   a value Pave will not accept, set back to Pave's default

Agent defaults come from pave.sh, in PAVE_AGENT_DEFAULTS
("analyst=sonnet:medium builder=sonnet:medium ..."), so they live in one place.

`fix` never rewrites the file. It edits the lines involved, keeping comments,
values and format (YAML or TOML), then re-reads the result and writes it only
if it parses to exactly the intended config and those findings are gone.
Exit 1 when the config cannot be read, or the fix cannot be made safely.
"""
import json
import os
import re
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path

HERE = Path(__file__).resolve().parent


def _yaml_reader():
    loader = SourceFileLoader("pave_yaml_reader", str(HERE / "yaml-reader"))
    mod = module_from_spec(spec_from_loader(loader.name, loader))
    loader.exec_module(mod)
    return mod


yr = _yaml_reader()


class ConfigError(Exception):
    pass


class CannotEdit(Exception):
    pass


# ---------------------------------------------------------------- what Pave reads

# Settings the skills read, with the values they accept and Pave's default.
SETTINGS = {
    ("execution", "mode"): (("parallel", "sequential"), "parallel"),
    ("execution", "monorepo_strategy"): (("sequential", "worktree", "shared-tree"), "sequential"),
    ("execution", "max_parallel"): ("a whole number of at least 1", 4),
    ("branch", "pattern"): ("text containing {feature-id}", "feature/{feature-id}"),
    ("contracts", "land_contracts"): ("true or false", True),
}
SECTIONS = ("agents", "execution", "branch", "contracts")

# Keys Pave no longer reads. A tuple names the key that replaced it; None
# means nothing did.
MOVED = {
    ("agents", "designer"): ("agents", "planner"),
    ("agents", "advisor"): ("agents", "retriever"),
    ("contracts", "land_before_fanout"): ("contracts", "land_contracts"),
}
GONE = {"model_ranking", "hub"}
PHASES = {"analyse": "analyst", "design": "planner", "build": "builder", "review": "reviewer"}


def agent_defaults():
    out = {}
    for item in os.environ.get("PAVE_AGENT_DEFAULTS", "").split():
        name, _, pair = item.partition("=")
        model, _, effort = pair.partition(":")
        out[name] = {"model": model, "effort": effort}
    if not out:
        raise ConfigError("PAVE_AGENT_DEFAULTS is not set - run this through pave.sh")
    return out


def valid(path, v):
    if path == ("execution", "max_parallel"):
        return isinstance(v, int) and not isinstance(v, bool) and v >= 1
    if path == ("branch", "pattern"):
        return isinstance(v, str) and "{feature-id}" in v
    if path == ("contracts", "land_contracts"):
        return isinstance(v, bool)
    return v in SETTINGS[path][0]


def fixed_value(path, v):
    if path == ("branch", "pattern") and isinstance(v, str) and "{feature-slug}" in v:
        return v.replace("{feature-slug}", "{feature-id}")
    return SETTINGS[path][1]


class Finding:
    def __init__(self, kind, path, text, op):
        self.kind, self.path, self.text, self.op = kind, tuple(path), text, op

    @property
    def key(self):
        return (self.kind, self.path)


def dotted(path):
    return ".".join(path) if path else "(top level)"


def is_text(v):
    return isinstance(v, str) and v.strip() != ""


def check(data, defaults):
    out = []
    if not isinstance(data, dict):
        return [Finding("invalid", (), "the config must be a mapping of keys", None)]

    agents = data.get("agents")
    agents_ok = agents is None or isinstance(agents, dict)
    have = agents if isinstance(agents, dict) else {}
    carry = {}  # agent -> (source, entry) for values moving in from elsewhere
    supplied = set()  # agents a rename provides

    for key, v in data.items():
        if key in SECTIONS:
            continue
        if key == "phases":
            moves = []
            for ph, entry in (v.items() if isinstance(v, dict) else []):
                tgt = PHASES.get(ph)
                if tgt and tgt not in have and isinstance(entry, dict):
                    carry[tgt] = ("phases." + ph, entry)
                    moves.append(f"phases.{ph} → agents.{tgt}")
            text = "replaced by agents"
            if moves:
                text += " (" + ", ".join(moves) + ")"
            out.append(Finding("leftover", (key,), text + " - remove it", ("remove", (key,))))
        elif key in GONE:
            out.append(Finding("leftover", (key,), "no longer used - remove it", ("remove", (key,))))
        else:
            out.append(Finding("leftover", (key,), "Pave does not read it - remove it", ("remove", (key,))))

    if not agents_ok:
        out.append(Finding("invalid", ("agents",), "must be a mapping of agent entries - fix by hand", None))
    for name, entry in have.items():
        path = ("agents", name)
        if name in defaults:
            out += check_agent(path, entry, defaults[name])
        elif path in MOVED:
            tgt = MOVED[path]
            if tgt[1] in have or tgt[1] in supplied:
                out.append(Finding("leftover", path, f"no longer read, and {dotted(tgt)} is set - remove it",
                                   ("remove", path)))
            else:
                supplied.add(tgt[1])
                out.append(Finding("leftover", path, f"renamed - becomes {dotted(tgt)}",
                                   ("rename", path, tgt[1])))
        else:
            out.append(Finding("leftover", path, "not a Pave agent - remove it", ("remove", path)))

    if agents_ok:
        for name, dflt in defaults.items():
            if name in have or name in supplied:
                continue
            entry, why = dict(dflt), "runs on Pave's default"
            if name in carry:
                src, old = carry[name]
                for k in ("model", "effort"):
                    if is_text(old.get(k)):
                        entry[k] = old[k]
                why = f"no entry - add it with {src}'s value"
            out.append(Finding("missing", ("agents", name), why, ("add", name, entry)))

    for section in SECTIONS[1:]:
        if section not in data:
            continue
        v = data[section]
        if not isinstance(v, dict):
            out.append(Finding("invalid", (section,), "must be a mapping - fix by hand", None))
            continue
        for key, x in v.items():
            path = (section, key)
            if path in SETTINGS:
                if not valid(path, x):
                    new = fixed_value(path, x)
                    out.append(Finding("invalid", path,
                                       f"is {fmt_plain(x)}, must be {accepted(path)} - set to {fmt_plain(new)}",
                                       ("set", path, new)))
            elif path in MOVED:
                tgt = MOVED[path]
                if tgt[1] in v:
                    out.append(Finding("leftover", path, f"no longer read, and {dotted(tgt)} is set - remove it",
                                       ("remove", path)))
                else:
                    out.append(Finding("leftover", path, f"renamed - becomes {dotted(tgt)}",
                                       ("rename", path, tgt[1])))
                    if not valid(tgt, x):
                        new = fixed_value(tgt, x)
                        out.append(Finding("invalid", tgt,
                                           f"is {fmt_plain(x)}, must be {accepted(tgt)} - set to {fmt_plain(new)}",
                                           ("set", tgt, new)))
            else:
                out.append(Finding("leftover", path, "Pave does not read it - remove it", ("remove", path)))
    return out


def check_agent(path, entry, dflt):
    if not isinstance(entry, dict):
        return [Finding("invalid", path, f"is {fmt_plain(entry)}, must be a model and an effort"
                        f" - set to {fmt_plain(dflt)}", ("set", path, dict(dflt)))]
    out = []
    for k, v in entry.items():
        p = path + (k,)
        if k not in ("model", "effort"):
            out.append(Finding("leftover", p, "Pave does not read it - remove it", ("remove", p)))
        elif not is_text(v):
            out.append(Finding("invalid", p, f"is {fmt_plain(v)}, must be a name - set to {dflt[k]}",
                               ("set", p, dflt[k])))
    return out


def accepted(path):
    rule = SETTINGS[path][0]
    return " or ".join(rule) if isinstance(rule, tuple) else rule


def fmt_plain(v):
    if v is None:
        return "empty"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k}: {fmt_plain(x)}" for k, x in v.items()) + " }"
    if isinstance(v, list):
        return "[" + ", ".join(fmt_plain(x) for x in v) + "]"
    return str(v)


# ---------------------------------------------------------------- the same ops on data


def apply_to_data(data, op):
    kind = op[0]
    if kind == "add":
        if data.get("agents") is None:
            data["agents"] = {}
        data["agents"][op[1]] = dict(op[2])
        return
    path = op[1]
    parent = data
    for k in path[:-1]:
        parent = parent[k]
    if kind == "remove":
        del parent[path[-1]]
    elif kind == "rename":
        parent[op[2]] = parent.pop(path[-1])
    elif kind == "set":
        parent[path[-1]] = op[2]


# ---------------------------------------------------------------- shared line helpers


def split_nl(text):
    lines = text.splitlines(keepends=True)
    nl = "\r\n" if lines and lines[0].endswith("\r\n") else "\n"
    return lines, nl


def body(line):
    return line.rstrip("\r\n")


def ending(line, nl):
    return line[len(body(line)):] or nl


def swap_value(line, a, b, new, nl):
    """Replace line[a:b] with new, keeping any comment after it in its column."""
    text, end = body(line), ending(line, nl)
    rest = text[b:]
    if rest.strip():
        gap = len(rest) - len(rest.lstrip())
        gap = max(1, gap - (len(new) - (b - a)))
        rest = " " * gap + rest.lstrip()
    return text[:a] + new + rest + end


def cut(lines, gone):
    """lines without the indices in gone, and no doubled blank line where they were."""
    out = []
    for j, x in enumerate(lines):
        if j in gone:
            continue
        if not x.strip() and (j - 1 in gone) and (not out or not out[-1].strip()):
            continue
        out.append(x)
    return out


def flow_items(inner):
    try:
        return yr.split_flow(inner, 0)
    except yr.YamlError as e:
        raise CannotEdit(str(e))


def flow_edit(line, vstart, vend, key, sep, new_item, nl):
    """Edit one item of the inline table line[vstart:vend]; new_item None removes it."""
    seg = body(line)[vstart:vend]
    if not (seg.startswith("{") and seg.endswith("}")):
        raise CannotEdit("expected an inline table")
    inner = seg[1:-1]
    items, hit = [], False
    for item in flow_items(inner):
        m = re.match(r"""^(["']?)([A-Za-z0-9_-]+)\1\s*""" + re.escape(sep), item)
        if m and m.group(2) == key:
            hit = True
            if new_item is not None:
                items.append(new_item)
        else:
            items.append(item)
    if not hit:
        raise CannotEdit(f"{key} not found in {seg}")
    pad = " " if inner.startswith(" ") else ""
    new = "{" + pad + ", ".join(items) + pad + "}" if items else "{}"
    return swap_value(line, vstart, vend, new, nl)


# ---------------------------------------------------------------- YAML

Y_KEY = re.compile(r"""^( *)(["']?)([A-Za-z_][A-Za-z0-9_-]*)\2[ \t]*:(?=\s|$)[ \t]*""")


def y_text(line):
    return yr.strip_comment(body(line)).rstrip()


def y_blank(line):
    return y_text(line).strip() in ("", "---", "...")


def y_indent(line):
    return len(line) - len(line.lstrip(" "))


def y_key(line):
    m = Y_KEY.match(y_text(line))
    return (m.group(3), m) if m else (None, None)


def y_value(line):
    """(start, end, text) of the value on a key line."""
    _, m = y_key(line)
    t = y_text(line)
    return m.end(), len(t), t[m.end():]


def y_span(lines, i):
    d = y_indent(lines[i])
    j = i + 1
    while j < len(lines) and (y_blank(lines[j]) or y_indent(lines[j]) > d):
        j += 1
    while j > i + 1 and y_blank(lines[j - 1]) and (not body(lines[j - 1]).strip() or y_indent(lines[j - 1]) <= d):
        j -= 1
    return j


def y_children(lines, start, end):
    rows = [i for i in range(start, end) if not y_blank(lines[i])]
    if not rows:
        return []
    ind = y_indent(lines[rows[0]])
    out = []
    for i in rows:
        if y_indent(lines[i]) != ind:
            continue
        if body(lines[i]).lstrip().startswith("-"):
            raise CannotEdit("lists are not edited")
        k, _ = y_key(lines[i])
        if k is None:
            raise CannotEdit(f"cannot read line {i + 1}")
        out.append((i, k))
    return out


def y_locate(lines, path):
    """('block', i) for a key on its own line, ('flow', i) for an item of the inline table on line i."""
    start, end = 0, len(lines)
    for depth, k in enumerate(path):
        hits = [i for i, key in y_children(lines, start, end) if key == k]
        if not hits:
            raise CannotEdit(f"{dotted(path)} not found")
        i = hits[0]
        if depth == len(path) - 1:
            return "block", i
        val = y_value(lines[i])[2]
        if val:
            if val.startswith("{") and depth == len(path) - 2:
                return "flow", i
            raise CannotEdit(f"{dotted(path[:depth + 1])} is written inline")
        start, end = i + 1, y_span(lines, i)
    raise CannotEdit("empty path")


def y_scalar(v, quote=None, flow=False):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k}: {y_scalar(x, flow=True)}" for k, x in v.items()) + " }"
    s = str(v)
    plain = re.fullmatch(r"[A-Za-z0-9_./-][A-Za-z0-9_./{} -]*", s) and not s.endswith(" ")
    if flow and re.search(r"[{}]", s):
        plain = False
    if quote or not plain or s.lower() in ("true", "false", "yes", "no", "on", "off", "null", "~") \
            or re.fullmatch(r"-?\d+(\.\d+)?", s):
        q = quote or '"'
        return q + s + q if q == "'" else json.dumps(s)
    return s


class Yaml:
    def __init__(self, text):
        self.lines, self.nl = split_nl(text)

    def text(self):
        return "".join(self.lines)

    def rename(self, path, new):
        kind, i = y_locate(self.lines, path)
        if kind != "block":
            raise CannotEdit(f"{dotted(path)} is written inline")
        _, m = y_key(self.lines[i])
        line, rest = self.lines[i], self.lines[i][m.end(3):]
        colon = rest.index(":") + 1
        gap = len(rest[colon:]) - len(rest[colon:].lstrip(" "))
        if gap > 1 and rest[colon:].strip():
            rest = rest[:colon] + " " * max(1, gap - (len(new) - len(m.group(3)))) + rest[colon + gap:]
            self.lines[i] = line[:m.start(3)] + new + rest
        else:
            a, b = m.start(3), len(y_text(line))
            self.lines[i] = swap_value(line, a, b, new + y_text(line)[m.end(3):], self.nl)

    def remove(self, path):
        kind, i = y_locate(self.lines, path)
        if kind == "block":
            self.lines = cut(self.lines, set(range(i, y_span(self.lines, i))))
        else:
            a, b, _ = y_value(self.lines[i])
            self.lines[i] = flow_edit(self.lines[i], a, b, path[-1], ":", None, self.nl)

    def set(self, path, value):
        kind, i = y_locate(self.lines, path)
        line = self.lines[i]
        a, b, old = y_value(line)
        if kind == "flow":
            self.lines[i] = flow_edit(line, a, b, path[-1], ":", f"{path[-1]}: {y_scalar(value, flow=True)}", self.nl)
            return
        quote = old[0] if old[:1] in ("'", '"') and not isinstance(value, (bool, int, dict)) else None
        new = y_scalar(value, quote)
        if b == a:
            new = " " + new if not body(line)[:a].endswith(" ") else new
        end = y_span(self.lines, i)
        self.lines[i] = swap_value(line, a, b, new, self.nl)
        del self.lines[i + 1:end]

    def add_agent(self, name, entry):
        flow = y_scalar(entry)
        top = y_children(self.lines, 0, len(self.lines))
        hits = [i for i, k in top if k == "agents"]
        if not hits:
            self._append(["agents:", f"  {name}: {flow}"])
            return
        i = hits[0]
        a, b, val = y_value(self.lines[i])
        if val == "{}":
            self.lines[i] = swap_value(self.lines[i], a, b, "", self.nl).rstrip(" \r\n") + ending(self.lines[i], self.nl)
            self.lines.insert(i + 1, f"  {name}: {flow}{self.nl}")
            return
        if val:
            raise CannotEdit("agents is written inline")
        end = y_span(self.lines, i)
        kids = y_children(self.lines, i + 1, end)
        if not kids:
            self.lines.insert(i + 1, f"  {name}: {flow}{self.nl}")
            return
        ind = y_indent(self.lines[kids[0][0]])
        at = y_span(self.lines, kids[-1][0])
        first = self.lines[kids[0][0]]
        fa, _, fval = y_value(first)
        if fval.startswith("{"):
            head = " " * ind + name + ":"
            col = body(first).index("{", fa)
            new = [head + " " * max(1, col - len(head)) + flow]
        else:
            sub = [j for j in range(kids[0][0] + 1, y_span(self.lines, kids[0][0])) if not y_blank(self.lines[j])]
            step = (y_indent(self.lines[sub[0]]) - ind) if sub else 2
            pad = " " * (ind + step)
            new = [" " * ind + name + ":"] + [f"{pad}{k}: {y_scalar(v)}" for k, v in entry.items()]
        self.lines[at:at] = [x + self.nl for x in new]

    def _append(self, new):
        if self.lines and not self.lines[-1].endswith(("\n", "\r")):
            self.lines[-1] += self.nl
        if self.lines and body(self.lines[-1]).strip():
            self.lines.append(self.nl)
        self.lines += [x + self.nl for x in new]


# ---------------------------------------------------------------- TOML

T_PART = r"""(?:[A-Za-z0-9_-]+|"[^"\\]*"|'[^']*')"""
T_DOTTED = rf"{T_PART}(?:\s*\.\s*{T_PART})*"
T_HEADER = re.compile(rf"^(\s*)(\[\[?)\s*({T_DOTTED})\s*(\]\]?)")
T_KEY = re.compile(rf"^(\s*)({T_DOTTED})\s*=\s*")


def t_parts(raw):
    return [p.strip() for p in re.findall(rf"{T_PART}", raw)]


def t_unquote(p):
    return p[1:-1] if p[:1] in "\"'" else p


def t_text(line):
    """The line up to any comment, with string contents respected."""
    s, i, q = body(line), 0, None
    while i < len(s):
        c = s[i]
        if q:
            if c == "\\" and q == '"':
                i += 1
            elif c == q:
                q = None
        elif c in "\"'":
            q = c
        elif c == "#":
            return s[:i].rstrip()
        i += 1
    return s.rstrip()


def t_depth(text):
    d, q, i = 0, None, 0
    while i < len(text):
        c = text[i]
        if q:
            if c == "\\" and q == '"':
                i += 1
            elif c == q:
                q = None
        elif c in "\"'":
            q = c
        elif c in "[{":
            d += 1
        elif c in "]}":
            d -= 1
        i += 1
    return d


class TomlRow:
    def __init__(self, kind, i, end, table, parts=None, raws=None, m=None, arr=False):
        self.kind, self.i, self.end, self.table = kind, i, end, table
        self.parts, self.raws, self.m, self.arr = parts, raws, m, arr

    @property
    def full(self):
        return self.table + tuple(self.parts)


class Toml:
    def __init__(self, text):
        if '"""' in text or "'''" in text:
            raise CannotEdit("multi-line strings are not edited")
        self.lines, self.nl = split_nl(text)

    def text(self):
        return "".join(self.lines)

    def rows(self):
        out, table, i, n = [], (), 0, len(self.lines)
        while i < n:
            t = t_text(self.lines[i])
            h = T_HEADER.match(t)
            if h and t.strip().startswith("["):
                raws = t_parts(h.group(3))
                table = tuple(t_unquote(p) for p in raws)
                out.append(TomlRow("header", i, i + 1, table, list(table), raws, h, h.group(2) == "[["))
                i += 1
                continue
            k = T_KEY.match(t)
            if k:
                raws = t_parts(k.group(2))
                end, d = i + 1, t_depth(t)
                while d > 0 and end < n:
                    d += t_depth(t_text(self.lines[end]))
                    end += 1
                out.append(TomlRow("key", i, end, table, [t_unquote(p) for p in raws], raws, k))
                i = end
                continue
            if t.strip():
                raise CannotEdit(f"cannot read line {i + 1}")
            i += 1
        return out

    def body_end(self, rows, h):
        nxt = [r.i for r in rows if r.kind == "header" and r.i > h.i]
        j = nxt[0] if nxt else len(self.lines)
        while j > h.i + 1 and not t_text(self.lines[j - 1]).strip():
            j -= 1
        return j

    def _inline_parent(self, rows, path):
        for r in rows:
            if r.kind == "key" and r.full == path[:-1] and r.end == r.i + 1:
                t = t_text(self.lines[r.i])
                if t[r.m.end():].startswith("{"):
                    return r
        raise CannotEdit(f"{dotted(path)} not found")

    def rename(self, path, new):
        rows, idx, hit = self.rows(), len(path) - 1, False
        for r in rows:
            if r.full[:len(path)] != path:
                continue
            if r.kind == "header":
                raws = list(r.raws)
                raws[idx] = new
                line = self.lines[r.i]
                self.lines[r.i] = line[:r.m.start(3)] + ".".join(raws) + line[r.m.end(3):]
                hit = True
            elif idx >= len(r.table):
                raws = list(r.raws)
                raws[idx - len(r.table)] = new
                line = self.lines[r.i]
                self.lines[r.i] = line[:r.m.start(2)] + ".".join(raws) + line[r.m.end(2):]
                hit = True
        if not hit:
            raise CannotEdit(f"{dotted(path)} is written inline")

    def remove(self, path):
        rows, spans = self.rows(), []
        for r in rows:
            if r.full[:len(path)] != path:
                continue
            spans.append((r.i, self.body_end(rows, r) if r.kind == "header" else r.end))
        if not spans:
            r = self._inline_parent(rows, path)
            t = t_text(self.lines[r.i])
            self.lines[r.i] = flow_edit(self.lines[r.i], r.m.end(), len(t), path[-1], "=", None, self.nl)
            return
        self.lines = cut(self.lines, {j for a, b in spans for j in range(a, b)})

    def set(self, path, value):
        rows = self.rows()
        hits = [r for r in rows if r.kind == "key" and r.full == path]
        if hits:
            r = hits[0]
            line = self.lines[r.i]
            t = t_text(line) if r.end == r.i + 1 else body(line)
            self.lines[r.i] = swap_value(line, r.m.end(), len(t), t_scalar(value), self.nl)
            del self.lines[r.i + 1:r.end]
            return
        r = self._inline_parent(rows, path)
        t = t_text(self.lines[r.i])
        self.lines[r.i] = flow_edit(self.lines[r.i], r.m.end(), len(t), path[-1], "=",
                                    f"{path[-1]} = {t_scalar(value)}", self.nl)

    def add_agent(self, name, entry):
        rows = self.rows()
        inline = t_scalar(entry)
        heads = [r for r in rows if r.kind == "header" and not r.arr]
        agents = [r for r in heads if r.table == ("agents",)]
        if agents:
            h = agents[0]
            end = self.body_end(rows, h)
            keys = [r for r in rows if r.kind == "key" and h.i < r.i < end]
            at = keys[-1].end if keys else h.i + 1
            self.lines.insert(at, f"{name} = {inline}{self.nl}")
            return
        subs = [r for r in heads if r.table[:1] == ("agents",)]
        if subs:
            at = self.body_end(rows, subs[-1])
            block = ["", f"[agents.{name}]"] + [f"{k} = {t_scalar(v)}" for k, v in entry.items()]
            self.lines[at:at] = [x + self.nl for x in block]
            return
        root = [r for r in rows if r.kind == "key" and r.table == () and r.parts[:1] == ["agents"]]
        if root:
            if any(len(r.parts) == 1 for r in root):
                raise CannotEdit("agents is written inline")
            self.lines.insert(root[-1].end, f"agents.{name} = {inline}{self.nl}")
            return
        if self.lines and not self.lines[-1].endswith(("\n", "\r")):
            self.lines[-1] += self.nl
        block = ([""] if self.lines and body(self.lines[-1]).strip() else []) + \
            [f"[agents.{name}]"] + [f"{k} = {t_scalar(v)}" for k, v in entry.items()]
        self.lines += [x + self.nl for x in block]


def t_scalar(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, int):
        return str(v)
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k} = {t_scalar(x)}" for k, x in v.items()) + " }"
    return json.dumps(str(v), ensure_ascii=False)


# ---------------------------------------------------------------- reading and reporting


def is_toml(path):
    return str(path).endswith(".toml")


def load(path, text):
    if is_toml(path):
        try:
            import tomllib
        except ModuleNotFoundError:
            try:
                import tomli as tomllib
            except ModuleNotFoundError:
                raise ConfigError("reading TOML needs Python 3.11+, or the tomli package")
        try:
            return tomllib.loads(text)
        except tomllib.TOMLDecodeError as e:
            raise ConfigError(f"{path}: {e}")
    try:
        return yr.load(text)
    except yr.YamlError as e:
        raise ConfigError(f"{path}: {e}")


def read(path):
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return f.read()
    except OSError as e:
        raise ConfigError(str(e))


def show_add(path, name, entry):
    if is_toml(path):
        return f"{name} = {t_scalar(entry)}"
    return f"{name}: {y_scalar(entry)}"


def line(path, f, label=None):
    head = f"{label or f.kind:<9} {dotted(f.path)}: "
    if f.op and f.op[0] == "add":
        return head + f"{f.text} - add  {show_add(path, f.op[1], f.op[2])}"
    return head + f.text


ORDER = {"rename": 0, "set": 1, "remove": 2, "add": 3}


def fix(path, text, findings):
    try:
        ed = Toml(text) if is_toml(path) else Yaml(text)
    except CannotEdit as e:
        raise ConfigError(f"cannot edit {path} line by line ({e}) - nothing written; fix by hand")
    expected = load(path, text)
    done, skipped = [], []
    for f in sorted([f for f in findings if f.op], key=lambda f: ORDER[f.op[0]]):
        kind, args = f.op[0], f.op[1:]
        try:
            if kind == "add":
                ed.add_agent(*args)
            else:
                getattr(ed, kind)(*args)
        except CannotEdit as e:
            skipped.append((f, str(e)))
            continue
        apply_to_data(expected, f.op)
        done.append(f)
    new = ed.text()
    try:
        got = load(path, new)
    except ConfigError as e:
        raise ConfigError(f"the edited config would not parse ({e}) - nothing written")
    if got != expected:
        raise ConfigError("the edited config would not read as intended - nothing written; fix by hand")
    return new, done, skipped


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("check", "fix", "count"):
        sys.exit("usage: pave-config.py <check|fix|count> <config>")
    mode, path = sys.argv[1], sys.argv[2]
    try:
        defaults = agent_defaults()
        text = read(path)
        findings = check(load(path, text), defaults)
        if mode == "count":
            print(len(findings))
            return
        print(f"config: {path}")
        if mode == "check":
            for f in findings:
                print(line(path, f))
            n = len(findings)
            print("result: nothing to fix" if not n else
                  f"result: {n} to fix - run /pave:init to review and apply them")
            return
        if not findings:
            print("result: nothing to fix")
            return
        new, done, skipped = fix(path, text, findings)
        remaining = check(load(path, new), defaults)
        left = {f.key for f in remaining}
        if any(f.key in left for f in done):
            raise ConfigError("a fix did not take - nothing written; fix by hand")
        if done:
            with open(path, "w", encoding="utf-8", newline="") as fh:
                fh.write(new)
        for f in done:
            print(line(path, f, "fixed"))
        for f, why in skipped:
            print(line(path, f, "by hand") + f" ({why})")
        for f in findings:
            if not f.op:
                print(line(path, f, "by hand"))
        print("result: nothing to fix" if not remaining else
              f"result: {len(remaining)} left to fix by hand")
    except ConfigError as e:
        sys.exit(f"pave-config: {e}")


if __name__ == "__main__":
    main()
