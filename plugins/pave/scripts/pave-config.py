#!/usr/bin/env python3
"""Compare a hub's config with the template this version of Pave ships, and fix it.

    pave-config.py check <config> <template>
    pave-config.py fix <config> <template> <add|remove|all>

The template is what Pave reads, so the comparison is right however old the
config is. `check` reports, one line each:

  leftover  a key the template does not have
  missing   a key the template has and the config does not

`fix` adds the missing keys with the template's values (add), removes the
leftovers (remove), or both (all). It reads the config, changes the data and
writes the file again in its own format. The file's opening comment block is
kept; other comments and layout are not. It writes nothing unless the new file
reads back as exactly the intended config.
Exit 1 when a file cannot be read, or the fix cannot be written safely.
"""
import copy
import json
import re
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path


class ConfigError(Exception):
    pass


def yaml_reader():
    path = Path(__file__).resolve().parent / "yaml-reader"
    loader = SourceFileLoader("pave_yaml_reader", str(path))
    mod = module_from_spec(spec_from_loader(loader.name, loader))
    loader.exec_module(mod)
    return mod


def is_toml(path):
    return path.endswith(".toml")


def parse(path, text):
    try:
        if is_toml(path):
            try:
                import tomllib
            except ModuleNotFoundError:
                try:
                    import tomli as tomllib
                except ModuleNotFoundError:
                    raise ConfigError("reading TOML needs Python 3.11+, or the tomli package")
            return tomllib.loads(text)
        return yaml_reader().load(text)
    except ConfigError:
        raise
    except Exception as e:  # a parse error from either reader
        raise ConfigError(f"{path}: {e}")


def read(path):
    try:
        with open(path, encoding="utf-8") as f:
            return f.read()
    except OSError as e:
        raise ConfigError(str(e))


def show(v):
    if v is None:
        return "(empty)"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{k}: {show(x)}" for k, x in v.items()) + " }"
    if isinstance(v, list):
        return "[" + ", ".join(show(x) for x in v) + "]"
    return str(v)


# ---------------------------------------------------------------- compare


def diff(config, template, path=()):
    """(kind, path, value) for every leftover and missing key."""
    config = config if isinstance(config, dict) else {}
    for key, v in config.items():
        if key not in template:
            yield "leftover", path + (key,), v
        elif isinstance(template[key], dict) and isinstance(v, dict):
            yield from diff(v, template[key], path + (key,))
    for key, v in template.items():
        if key not in config:
            yield "missing", path + (key,), v


def line(kind, path, v):
    return f"{kind:<9} {'.'.join(map(str, path))} = {show(v)}"


def apply(config, found, mode):
    out = copy.deepcopy(config)
    for kind, path, v in found:
        if kind == "leftover" and mode in ("remove", "all"):
            parent = out
            for k in path[:-1]:
                parent = parent[k]
            del parent[path[-1]]
        elif kind == "missing" and mode in ("add", "all"):
            parent = out
            for k in path[:-1]:
                if not isinstance(parent.get(k), dict):
                    parent[k] = {}
                parent = parent[k]
            parent[path[-1]] = copy.deepcopy(v)
    return out


# ---------------------------------------------------------------- write

PLAIN = re.compile(r"[A-Za-z_./-][A-Za-z0-9_./{} -]*")
BARE_KEY = re.compile(r"[A-Za-z0-9_-]+")


def y_scalar(v, flow):
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(y_scalar(x, True) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{y_key(k)}: {y_scalar(x, True)}" for k, x in v.items()) + " }" if v else "{}"
    s = str(v)
    plain = PLAIN.fullmatch(s) and not s.endswith(" ") \
        and s.lower() not in ("true", "false", "yes", "no", "on", "off", "null", "~") \
        and not (flow and re.search(r"[{}]", s))
    return s if plain else json.dumps(s, ensure_ascii=False)


def y_key(k):
    return k if BARE_KEY.fullmatch(str(k)) else json.dumps(str(k))


def to_yaml(data):
    """Sections as blocks; a mapping of plain values inside them on one line."""
    out = []

    def block(d, ind):
        for k, v in d.items():
            nested = isinstance(v, dict) and v and (ind == 0 or any(isinstance(x, dict) for x in v.values()))
            if ind == 0 and out and (nested or isinstance(v, dict)):
                out.append("")
            if nested:
                out.append(f"{' ' * ind}{y_key(k)}:")
                block(v, ind + 2)
            else:
                out.append(f"{' ' * ind}{y_key(k)}: {y_scalar(v, False)}")

    block(data, 0)
    return "\n".join(out) + "\n"


def t_value(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return str(v)
    if isinstance(v, list):
        return "[" + ", ".join(t_value(x) for x in v) + "]"
    if isinstance(v, dict):
        return "{ " + ", ".join(f"{t_key(k)} = {t_value(x)}" for k, x in v.items()) + " }" if v else "{}"
    if v is None:
        raise ConfigError("TOML has no empty value")
    return json.dumps(str(v), ensure_ascii=False)


def t_key(k):
    return k if BARE_KEY.fullmatch(str(k)) else json.dumps(str(k))


def to_toml(data):
    """Top-level values first, then one [table] per section, entries inline."""
    out = [f"{t_key(k)} = {t_value(v)}" for k, v in data.items() if not isinstance(v, dict)]
    for key, v in data.items():
        if isinstance(v, dict):
            if out:
                out.append("")
            out.append(f"[{t_key(key)}]")
            out += [f"{t_key(k)} = {t_value(x)}" for k, x in v.items()]
    return "\n".join(out) + "\n"


def header(text):
    """The file's opening comment block: its first lines, up to a blank line or a key."""
    lines = []
    for raw in text.splitlines():
        if not raw.lstrip().startswith("#"):
            break
        lines.append(raw)
    return "\n".join(lines) + "\n\n" if lines else ""


# ---------------------------------------------------------------- main


def main():
    args = sys.argv[1:]
    if not (args[:1] == ["check"] and len(args) == 3
            or args[:1] == ["fix"] and len(args) == 4 and args[3] in ("add", "remove", "all")):
        sys.exit("usage: pave-config.py check <config> <template>\n"
                 "       pave-config.py fix <config> <template> <add|remove|all>")
    cmd, path, tpath = args[0], args[1], args[2]
    try:
        text = read(path)
        config, template = parse(path, text), parse(tpath, read(tpath))
        if not isinstance(config, dict):
            raise ConfigError(f"{path}: expected a mapping of keys at the top level")
        found = list(diff(config, template))
        print(f"config: {path}")

        if cmd == "check":
            for f in found:
                print(line(*f))
            print(f"result: {len(found)} to fix - run /pave:init" if found else "result: nothing to fix")
            return

        mode = args[3]
        want = apply(config, found, mode)
        if want == config:
            print("result: nothing to change")
            return
        new = header(text) + (to_toml(want) if is_toml(path) else to_yaml(want))
        if parse(path, new) != want:
            raise ConfigError("the rewritten config would not read back as intended - nothing written")
        with open(path, "w", encoding="utf-8") as f:
            f.write(new)
        for kind, p, v in found:
            if (kind, mode) in (("leftover", "remove"), ("leftover", "all")):
                print(line("removed", p, v))
            elif (kind, mode) in (("missing", "add"), ("missing", "all")):
                print(line("added", p, v))
        left = list(diff(want, template))
        print(f"result: {len(left)} left - run /pave:init" if left else "result: nothing to fix")
    except ConfigError as e:
        sys.exit(f"pave-config: {e}")


if __name__ == "__main__":
    main()
