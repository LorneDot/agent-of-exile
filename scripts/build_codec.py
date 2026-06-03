#!/usr/bin/env python3
"""GGG PoE2 Build Encoder/Decoder.

Handles the deflate+base64 encoding used by Path of Exile 2's
official build planner import/export format.

Usage:
    python build_codec.py encode build.xml          # → build.txt (base64 string)
    python build_codec.py decode build.txt          # → stdout (XML)
    python build_codec.py decode build.txt -o out.xml

Python API:
    from build_codec import encode_build, decode_build
    encoded = encode_build(xml_string)
    xml_string = decode_build(encoded_string)
"""

from __future__ import annotations

import base64
import sys
import zlib
from pathlib import Path


def encode_build(xml: str) -> str:
    """Encode an XML build string to GGG build code.

    Pipeline: XML → deflate → base64 (URL-safe)
    """
    compressed = zlib.compress(xml.encode("utf-8"))
    encoded = base64.b64encode(compressed).decode("ascii")
    # URL-safe variant
    return encoded.replace("+", "-").replace("/", "_")


def decode_build(code: str) -> str:
    """Decode a GGG build code back to XML.

    Pipeline: base64 (URL-safe) → inflate → XML string
    """
    # Reverse URL-safe encoding
    normalized = code.replace("-", "+").replace("_", "/")
    # Ensure proper padding
    missing_padding = len(normalized) % 4
    if missing_padding:
        normalized += "=" * (4 - missing_padding)
    compressed = base64.b64decode(normalized)
    return zlib.decompress(compressed).decode("utf-8")


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Encode/decode PoE2 GGG build planner files"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    enc = sub.add_parser("encode", help="Encode XML to GGG build string")
    enc.add_argument("input", help="Path to XML file or '-' for stdin")
    enc.add_argument("-o", "--output", help="Output file (default: stdout)")

    dec = sub.add_parser("decode", help="Decode GGG build string to XML")
    dec.add_argument("input", help="Path to build string file or '-' for stdin")
    dec.add_argument("-o", "--output", help="Output file (default: stdout)")

    args = parser.parse_args()

    if args.input == "-":
        data = sys.stdin.read()
    else:
        data = Path(args.input).read_text()

    if args.command == "encode":
        result = encode_build(data)
    else:
        result = decode_build(data.strip())

    if args.output:
        Path(args.output).write_text(result)
    else:
        sys.stdout.write(result)


if __name__ == "__main__":
    cli()
