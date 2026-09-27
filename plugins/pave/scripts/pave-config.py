#!/usr/bin/env python3
"""Compare a hub's config with the template this version of Pave ships.

    pave-config.py <config> <template>

The template is what Pave reads, so the comparison is right however old the
config is. It reports, one line each:

  leftover  a key the template does not have
  missing   a key the template has and the config does not
  invalid   a value of a different kind from the template's

and ends with a result line. It changes nothing: /pave:init makes the edits.
Exit 1 when either file cannot be read.
"""
import sys
from importlib.machinery import SourceFileLoader
from importlib.util import module_from_spec, spec_from_loader
from pathlib import Path


def yaml_reader():
    path = Path(__file__).resolve().parent / "yaml-reader"
    loader = SourceFileLoader("pave_yaml_reader", str(path))
    mod = module_from_spec(spec_from_loader(loader.name, loader))
    loader.exec_module(mod)
    return mod


def load(path):
    try:
        if path.endswith(".toml"):
            try:
                import tomllib
            except ModuleNotFoundError:
                try:
                    import tomli as tomllib
                except ModuleNotFoundError:
                    sys.exit("pave-config: reading TOML needs Python 3.11+, or the tomli package")
            with open(path, "rb") as f:
                return tomllib.load(f)
        yr = yaml_reader()
        with open(path, encoding="utf-8") as f:
            return yr.load(f.read())
    except OSError as e:
        sys.exit(f"pave-config: {e}")
    except Exception as e:  # a parse error from either reader
        sys.exit(f"pave-config: {path}: {e}")


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


def kind(v):
    if isinstance(v, bool):
        return "true or false"
    if isinstance(v, (int, float)):
        return "a number"
    if isinstance(v, dict):
        return "a mapping"
    if isinstance(v, list):
        return "a list"
    return "text"


def compare(config, template, path=()):
    for key, v in config.items():
        p = ".".join(path + (str(key),))
        if key not in template:
            yield f"leftover  {p} = {show(v)}"
        elif isinstance(template[key], dict) and isinstance(v, dict):
            yield from compare(v, template[key], path + (key,))
        elif v is None or kind(v) != kind(template[key]):
            yield f"invalid   {p} = {show(v)} (template has {kind(template[key])}: {show(template[key])})"
    for key, v in template.items():
        if key not in config:
            yield f"missing   {'.'.join(path + (str(key),))} (template: {show(v)})"


def main():
    if len(sys.argv) != 3:
        sys.exit("usage: pave-config.py <config> <template>")
    config, template = load(sys.argv[1]), load(sys.argv[2])
    print(f"config: {sys.argv[1]}")
    if not isinstance(config, dict):
        print(f"invalid   (top level) = {show(config)} (template has a mapping)")
        print("result: 1 to fix - run /pave:init")
        return
    found = list(compare(config, template))
    for line in found:
        print(line)
    print(f"result: {len(found)} to fix - run /pave:init" if found else "result: nothing to fix")


if __name__ == "__main__":
    main()
