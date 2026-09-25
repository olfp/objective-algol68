#!/usr/bin/env python3
"""Convert upper-stropped Algol 68 source to Unicode-stropped .u68 source.

Upper-case words are rendered in Mathematical Bold and lower-case identifiers
are rendered in Mathematical Italic. Comments and string literals are copied
unchanged.
"""

from __future__ import annotations

import argparse
import re
import sys
import unicodedata
from pathlib import Path

IDENTIFIER = re.compile(r"[A-Za-z][A-Za-z0-9_]*")


def _math_letter(style: str, case: str, letter: str) -> str:
    name = f"MATHEMATICAL {style.upper()} {case.upper()} {letter.upper()}"
    try:
        return unicodedata.lookup(name)
    except KeyError:
        # A few mathematical alphabets use compatibility characters outside
        # the contiguous mathematical-alphanumeric Unicode blocks.
        exceptions = {
            ("italic", "capital", "C"): "ℂ",
            ("italic", "capital", "H"): "ℋ",
            ("italic", "capital", "I"): "ℐ",
            ("italic", "capital", "R"): "ℛ",
            ("italic", "capital", "Z"): "ℤ",
            ("italic", "small", "h"): "ℎ",
        }
        try:
            return exceptions[(style, case, letter)]
        except KeyError as exc:  # pragma: no cover - defensive programming
            raise ValueError(f"no Unicode mathematical {style} mapping for {letter}") from exc


def _styled_identifier(token: str) -> str:
    if token.isupper():
        style, case = "bold", "capital"
    elif token.islower():
        style, case = "italic", "small"
    else:
        # Algol 68 source conventions use all-upper words for stropped words
        # and all-lower words for names. Leave mixed-case extensions readable.
        return token

    return "".join(
        _math_letter(style, case, char) if char.isalpha() else char
        for char in token
    )


def convert(source: str) -> str:
    """Convert source while leaving comments and quoted strings unchanged."""
    output: list[str] = []
    i = 0
    n = len(source)
    state = "code"

    while i < n:
        char = source[i]

        if state == "comment":
            output.append(char)
            i += 1
            if char == "\n":
                state = "code"
            continue

        if state == "string":
            output.append(char)
            i += 1
            if char == "\\" and i < n:
                output.append(source[i])
                i += 1
            elif char == '"':
                state = "code"
            continue

        if char == "#":
            output.append(char)
            i += 1
            state = "comment"
            continue

        if char == '"':
            output.append(char)
            i += 1
            state = "string"
            continue

        match = IDENTIFIER.match(source, i)
        if match:
            output.append(_styled_identifier(match.group(0)))
            i = match.end()
            continue

        output.append(char)
        i += 1

    return "".join(output)


def output_path(input_path: Path) -> Path:
    if input_path.suffix.lower() == ".a68":
        return input_path.with_suffix(".u68")
    return input_path.with_name(input_path.name + ".u68")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Convert upper-stropped Algol 68 .a68 files to Unicode-stropped .u68 files."
    )
    parser.add_argument("source", type=Path, help="input Algol 68 source file")
    parser.add_argument("-o", "--output", type=Path, help="output file (default: derived .u68 path)")
    parser.add_argument("--stdout", action="store_true", help="write converted source to stdout")
    args = parser.parse_args(argv)

    text = args.source.read_text(encoding="utf-8")
    converted = convert(text)
    if args.stdout:
        sys.stdout.write(converted)
        return 0

    destination = args.output or output_path(args.source)
    destination.write_text(converted, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
