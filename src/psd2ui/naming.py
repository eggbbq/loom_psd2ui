import re
import unicodedata
from pathlib import Path

from .laya_types import new_ui_component


RESERVED_VARIABLE_NAMES = frozenset("""
await break case catch class const continue debugger default delete do else enum
export extends false finally for function if implements import in instanceof
interface let new null package private protected public return static super
switch this throw true try typeof var void while with yield eval arguments
""".split())


def is_variable_name(name: str) -> bool:
    """ECMAScript/TypeScript identifier, excluding strict-mode binding keywords."""
    def start(char):
        return (char in "$_" or unicodedata.category(char).startswith("L") or
                unicodedata.category(char) == "Nl" or char in "\u1885\u1886\u2118\u212e\u309b\u309c")
    def part(char):
        return (start(char) or unicodedata.category(char) in ("Mn", "Mc", "Nd", "Pc") or
                char in "\u00b7\u0387\u1369\u136a\u136b\u136c\u136d\u136e\u136f\u1370\u1371\u19da\u200c\u200d")
    return bool(name) and name not in RESERVED_VARIABLE_NAMES and start(name[0]) and all(part(c) for c in name[1:])


def layer_tag(raw: str):
    """Match the first underscore-delimited segment, or the entire name."""
    token, separator, _ = raw.partition("_")
    if new_ui_component(token):
        return token + separator
    return None


def tag_component(raw: str):
    tag = layer_tag(raw)
    if tag is None:
        return None
    token = tag[:-1] if tag.endswith("_") else tag
    return new_ui_component(token)


def untagged_name(raw: str) -> str:
    """Logical node name, before filesystem-safe normalization."""
    tag = layer_tag(raw)
    return raw[len(tag):] if tag and "_" in raw else raw


def export_name(raw: str) -> str:
    """One safe cross-platform path component; preserve legal Unicode and spaces."""
    name = untagged_name(raw).strip()
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f\x7f]', "_", name)
    name = name.replace("..", "_").rstrip(". ")
    if not name:
        raise ValueError("Name is empty after removing the tag and unsafe characters")
    if re.fullmatch(r"(?i:CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])(?:\..*)?", name):
        name = "_" + name
    return name


def inside(root: Path, relative: str) -> Path:
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ValueError(f"Path escapes output directory: {relative}")
    return path

