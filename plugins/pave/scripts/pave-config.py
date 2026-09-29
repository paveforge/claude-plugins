#!/usr/bin/env python3
"""Compare a hub's config with the template this version of Pave ships.

    pave-config.py <config> <template>

templates/config.yaml is the single source of truth for what Pave reads, so
the comparison is right however old the config is. It reports, one line each:

  leftover  a key the template does not have
  missing   a key the template has and the config does not

and ends with a result line. It changes nothing: /pave:init makes the edits.
Exit 1 when either file cannot be read.
"""
import sys

import pave_yaml


class ConfigError(Exception):
    pass


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
        return pave_yaml.load(text) or {}
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


# ---------------------------------------------------------------- main


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: pave-config.py <config> <template>")
    path, tpath = sys.argv[1], sys.argv[2]
    try:
        config, template = parse(path, read(path)), parse(tpath, read(tpath))
    except ConfigError as e:
        sys.exit(f"pave-config: {e}")
    if not isinstance(config, dict):
        sys.exit(f"pave-config: {path}: expected a mapping of keys at the top level")
    found = list(diff(config, template))
    print(f"config: {path}")
    for f in found:
        print(line(*f))
    print(f"result: {len(found)} to fix - run /pave:init" if found else "result: nothing to fix")


if __name__ == "__main__":
    main()
