"""YAML for every Pave script: the hub config, and the frontmatter models write.

A script reads a model-written file through this module, never with a regex:
a model may write any valid layout - block or flow, keys in any order - and
every one must read the same.

Uses PyYAML when installed. Otherwise a built-in parser reads the subset Pave
uses (block mappings and lists, flow {..} and [..] - nested and across lines -,
comments, plain or quoted scalars) and rejects anything else rather than
guessing. Both resolve plain scalars the same way: true/false/yes/no/on/off,
null/~, decimal ints and floats, and everything else as a string. A leading
zero keeps a number a string ("01"), and dates stay strings.

Writing stays a targeted text edit: set_key replaces one top-level key and
leaves every other line, comments included, as it was.
"""
import re

__all__ = ["YamlError", "load", "split_frontmatter", "read_frontmatter", "set_key", "flow"]


class YamlError(Exception):
    pass


BOOLS = {v: True for v in ("true", "True", "TRUE", "yes", "Yes", "YES", "on", "On", "ON")}
BOOLS.update({v: False for v in ("false", "False", "FALSE", "no", "No", "NO", "off", "Off", "OFF")})
NULLS = ("", "~", "null", "Null", "NULL")
INT = re.compile(r"[-+]?(?:0|[1-9][0-9]*)")
FLOAT = re.compile(r"[-+]?(?:0|[1-9][0-9]*)\.[0-9]+")
KEY = r"""("[^"]*"|'[^']*'|[^:\[\]{}#"'][^:#]*?)\s*:(?=\s|$)"""


def resolve(s):
    """A plain scalar's value."""
    if s in NULLS:
        return None
    if s in BOOLS:
        return BOOLS[s]
    if INT.fullmatch(s):
        return int(s)
    if FLOAT.fullmatch(s):
        return float(s)
    return s


# ---------------------------------------------------------------- built-in

class Flow:
    """A flow value: a scalar, or {..} and [..] nested to any depth."""

    def __init__(self, text, ln):
        self.s, self.i, self.ln = text, 0, ln

    def fail(self, msg):
        raise YamlError(f"line {self.ln}: {msg}")

    def ws(self):
        while self.i < len(self.s) and self.s[self.i] in " \t":
            self.i += 1

    def peek(self):
        self.ws()
        return self.s[self.i] if self.i < len(self.s) else ""

    def whole(self, block):
        v = self.value(block)
        if self.peek():
            self.fail(f"unexpected {self.s[self.i:]!r} after a value")
        return v

    def value(self, block=False):
        c = self.peek()
        if c == "[":
            return self.seq()
        if c == "{":
            return self.mapping()
        if c in "\"'":
            return self.quoted()
        return self.plain(block)

    def quoted(self):
        q = self.s[self.i]
        self.i += 1
        out = ""
        while self.i < len(self.s):
            c = self.s[self.i]
            if c == q:
                if q == "'" and self.s[self.i + 1:self.i + 2] == "'":
                    out += "'"
                    self.i += 2
                    continue
                self.i += 1
                return out
            if c == "\\" and q == '"':
                esc = self.s[self.i + 1:self.i + 2]
                if esc not in ('"', "\\", "n", "t", "/"):
                    self.fail(f"unsupported escape \\{esc} in a quoted string")
                out += {"n": "\n", "t": "\t"}.get(esc, esc)
                self.i += 2
                continue
            out += c
            self.i += 1
        self.fail(f"unterminated string {self.s}")

    def plain(self, block):
        start = self.i
        if block:
            text = self.s[start:].strip()
            self.i = len(self.s)
        else:
            while self.i < len(self.s):
                c = self.s[self.i]
                if c in ",[]{}":
                    break
                if c == ":" and self.s[self.i + 1:self.i + 2] in ("", " ", "\t", ",", "]", "}"):
                    break
                self.i += 1
            text = self.s[start:self.i].strip()
        if text[:1] in tuple("&*!|>@`%"):
            self.fail(f"unsupported YAML syntax {text!r}")
        if block and re.search(r":(\s|$)", text):
            self.fail(f"a plain value may not contain ': ' - quote it: {text!r}")
        return resolve(text)

    def seq(self):
        self.i += 1
        out = []
        while True:
            c = self.peek()
            if c == "]":
                self.i += 1
                return out
            if not c:
                self.fail("unclosed [")
            out.append(self.value())
            c = self.peek()
            if c == ",":
                self.i += 1
            elif c != "]":
                self.fail(f"expected , or ] in a list, got {c or 'end of line'!r}")

    def mapping(self):
        self.i += 1
        out = {}
        while True:
            c = self.peek()
            if c == "}":
                self.i += 1
                return out
            if not c:
                self.fail("unclosed {")
            if c in "[{":
                self.fail("a key must be a scalar")
            key = self.quoted() if c in "\"'" else self.plain(False)
            if self.peek() != ":":
                self.fail(f"expected key: value, got {key!r}")
            self.i += 1
            if key in out:
                self.fail(f"duplicate key {key}")
            c = self.peek()
            out[key] = None if c in (",", "}") else self.value()
            c = self.peek()
            if c == ",":
                self.i += 1
            elif c != "}":
                self.fail(f"expected , or }} in a mapping, got {c or 'end of line'!r}")


def value(s, ln):
    return Flow(s.strip(), ln).whole(block=True)


def strip_comment(line):
    quote = None
    for i, c in enumerate(line):
        if quote:
            if c == quote:
                quote = None
        elif c in "\"'" and (i == 0 or line[i - 1] in " \t[{,:-"):
            quote = c
        elif c == "#" and (i == 0 or line[i - 1] in " \t"):
            return line[:i]
    return line


def depth(s):
    """How many [ and { the text leaves open, outside quotes."""
    d, quote = 0, None
    for i, c in enumerate(s):
        if quote:
            if c == quote:
                quote = None
        elif c in "\"'" and (i == 0 or s[i - 1] in " \t[{,:-"):
            quote = c
        elif c in "[{":
            d += 1
        elif c in "]}":
            d -= 1
    return d


def flow_start(body):
    """The flow collection a line opens, if its value starts one."""
    rest = body
    while rest.startswith("- ") or rest == "-":
        rest = rest[1:].lstrip()
    m = re.match(KEY, rest)
    if m:
        rest = rest[m.end():].lstrip()
    return rest if rest[:1] in ("[", "{") else ""


def tokenize(text):
    rows, lines = [], text.splitlines()
    n = 0
    while n < len(lines):
        raw, ln = lines[n], n + 1
        n += 1
        if raw.strip() in ("---", "..."):
            continue
        line = strip_comment(raw).rstrip()
        if not line.strip():
            continue
        body = line.lstrip(" ")
        if body.startswith("\t") or "\t" in line[: len(line) - len(body)]:
            raise YamlError(f"line {ln}: tabs are not allowed for indentation")
        # A flow collection may run over several lines: join them.
        opened = flow_start(body)
        while opened and depth(opened) > 0:
            if n >= len(lines):
                raise YamlError(f"line {ln}: unclosed {opened[0]}")
            more = strip_comment(lines[n]).strip()
            n += 1
            body += " " + more
            opened += " " + more
        rows.append((len(line) - len(line.lstrip(" ")), body, ln))
    return rows


def is_item(body):
    return body.startswith("- ") or body == "-"


def parse_block(rows, i, indent):
    if is_item(rows[i][1]):
        return parse_list(rows, i, indent)
    return parse_map(rows, i, indent)


def child(rows, i, indent):
    if i < len(rows) and rows[i][0] > indent:
        return parse_block(rows, i, rows[i][0])
    # A list may sit at its key's own indentation.
    if i < len(rows) and rows[i][0] == indent and is_item(rows[i][1]):
        return parse_list(rows, i, indent, under_key=True)
    return None, i


def parse_map(rows, i, indent):
    out = {}
    while i < len(rows):
        ind, body, ln = rows[i]
        if ind < indent:
            break
        if ind > indent:
            raise YamlError(f"line {ln}: unexpected indentation")
        if body.startswith("-"):
            raise YamlError(f"line {ln}: list item where a key was expected")
        m = re.match(KEY + r"\s*(.*)$", body)
        if not m:
            raise YamlError(f"line {ln}: expected key: value, got {body!r}")
        key = m.group(1)
        key = key[1:-1] if key[:1] in "\"'" else resolve(key)
        if key in out:
            raise YamlError(f"line {ln}: duplicate key {key}")
        rest = m.group(2).strip()
        i += 1
        if rest:
            out[key] = value(rest, ln)
            if i < len(rows) and rows[i][0] > indent:
                raise YamlError(f"line {rows[i][2]}: unexpected indentation")
        else:
            out[key], i = child(rows, i, indent)
    return out, i


def parse_list(rows, i, indent, under_key=False):
    out = []
    while i < len(rows):
        ind, body, ln = rows[i]
        if ind < indent:
            break
        if under_key and ind == indent and not is_item(body):
            break
        if ind > indent or not is_item(body):
            raise YamlError(f"line {ln}: expected a list item")
        rest = body[1:].lstrip()
        col = indent + len(body) - len(rest)
        i += 1
        if not rest:
            item, i = child(rows, i, indent)
            out.append(item)
        elif re.match(KEY, rest):
            sub = [(col, rest, ln)]
            while i < len(rows) and rows[i][0] > indent:
                sub.append(rows[i])
                i += 1
            item, _ = parse_map(sub, 0, col)
            out.append(item)
        else:
            out.append(value(rest, ln))
            if i < len(rows) and rows[i][0] > indent:
                raise YamlError(f"line {rows[i][2]}: unexpected indentation")
    return out, i


def load_builtin(text):
    rows = tokenize(text)
    if not rows:
        return None
    if rows[0][0] != 0:
        raise YamlError(f"line {rows[0][2]}: top level must not be indented")
    if rows[0][1][:1] in ("[", "{"):
        if len(rows) > 1:
            raise YamlError(f"line {rows[1][2]}: unexpected content after a flow value")
        return value(rows[0][1], rows[0][2])
    data, i = parse_block(rows, 0, 0)
    if i < len(rows):
        raise YamlError(f"line {rows[i][2]}: unexpected content")
    return data


# ---------------------------------------------------------------- PyYAML

_loader = None


def pyyaml_loader(yaml):
    """SafeLoader, resolving plain scalars exactly as the built-in parser does,
    and refusing duplicate keys."""
    global _loader
    if _loader is not None:
        return _loader

    class Loader(yaml.SafeLoader):
        yaml_implicit_resolvers = {}

        def construct_mapping(self, node, deep=False):
            seen = []
            for k, _ in node.value:
                key = self.construct_object(k, deep=True)
                if key in seen:
                    raise yaml.constructor.ConstructorError(
                        None, None, f"duplicate key {key}", k.start_mark)
                seen.append(key)
            return super().construct_mapping(node, deep)

    def exact(words):
        return re.compile("^(?:" + "|".join(re.escape(w) for w in words) + ")$")

    Loader.add_implicit_resolver("tag:yaml.org,2002:bool", exact(BOOLS), list("tTfFyYnNoO"))
    Loader.add_implicit_resolver("tag:yaml.org,2002:null", exact(NULLS), ["~", "n", "N", ""])
    Loader.add_implicit_resolver("tag:yaml.org,2002:int", re.compile("^" + INT.pattern + "$"),
                                 list("-+0123456789"))
    Loader.add_implicit_resolver("tag:yaml.org,2002:float", re.compile("^" + FLOAT.pattern + "$"),
                                 list("-+0123456789"))
    _loader = Loader
    return Loader


def load(text):
    """The YAML document in text. An empty document is None."""
    try:
        import yaml
    except ImportError:
        return load_builtin(text)
    try:
        return yaml.load(text, Loader=pyyaml_loader(yaml))
    except yaml.YAMLError as e:
        raise YamlError(str(e).replace("\n", " "))


# ---------------------------------------------------------------- frontmatter

FRONTMATTER = re.compile(r"---[ \t]*\n(.*?\n)?---[ \t]*(?:\n|\Z)", re.S)


def split_frontmatter(text):
    """(frontmatter text, body), or (None, text) when there is none."""
    m = FRONTMATTER.match(text)
    if not m:
        return None, text
    return m.group(1) or "", text[m.end():]


def read_frontmatter(path, text=None):
    """(mapping, frontmatter text, body) of a Markdown file. The mapping is None
    when the file has no frontmatter. Frontmatter that does not parse, or is
    not a mapping, is an error naming the file - never "no data"."""
    text = path.read_text() if text is None else text
    fm, body = split_frontmatter(text)
    if fm is None:
        return None, None, body
    try:
        data = load(fm)
    except YamlError as e:
        raise YamlError(f"{path}: frontmatter does not parse: {e}")
    if data is None:
        data = {}
    if not isinstance(data, dict):
        raise YamlError(f"{path}: frontmatter is not a mapping of key: value")
    return data, fm, body


# ---------------------------------------------------------------- writing

def key_span(fm, key):
    """(start, end) of a top-level key in frontmatter text: its line and every
    line that belongs to its value. None when the key is absent."""
    lines = fm.splitlines(keepends=True)
    pat = re.compile(r"""^(?:{0}|"{0}"|'{0}')[ \t]*:(?:[ \t]|$)""".format(re.escape(key)))
    pos = 0
    for n, line in enumerate(lines):
        if pat.match(line):
            end, last = pos + len(line), pos + len(line)
            # A flow value may run over several lines, whatever their indentation.
            open_ = depth(flow_start(strip_comment(line.rstrip("\n"))))
            for more in lines[n + 1:]:
                end += len(more)
                if open_ > 0:
                    open_ += depth(strip_comment(more.rstrip("\n")))
                    last = end
                    continue
                if not more.strip():
                    continue
                if more[0] in " \t" or is_item(more.rstrip("\n")):
                    last = end
                    continue
                break
            return pos, last
        pos += len(line)
    return None


def set_key(fm, key, block, after=None):
    """fm with one top-level key replaced by block (its full text, `key: ...`).
    An absent key goes right after the key `after`, or at the end."""
    block = block.rstrip("\n") + "\n"
    span = key_span(fm, key)
    if span:
        return fm[:span[0]] + block + fm[span[1]:]
    anchor = key_span(fm, after) if after else None
    at = anchor[1] if anchor else len(fm)
    if at and fm[at - 1:at] != "\n":
        fm = fm[:at] + "\n" + fm[at:]
        at += 1
    return fm[:at] + block + fm[at:]


PLAIN_SAFE = re.compile(r"[A-Za-z0-9_./@<>=+~^-][^,\[\]{}#:\"'\n]*")


def flow(v):
    """v written as a flow value that reads back as v."""
    if isinstance(v, bool):
        return "true" if v else "false"
    if v is None:
        return "null"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(flow(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{flow(k)}: {flow(x)}" for k, x in v.items()) + " }"
    s = str(v)
    if PLAIN_SAFE.fullmatch(s) and s == s.strip() and resolve(s) == s:
        return s
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n") + '"'
