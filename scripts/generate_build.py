#!/usr/bin/env python3
"""Generate a GGG-compatible PoE2 build file from a build specification.

Takes a JSON build spec and produces the deflate+base64-encoded
build string that can be imported into the official PoE2 build planner.

Build Spec Format (JSON):
{
    "className": "Witch",
    "ascendClassName": "Infernalist",
    "level": 80,
    "passives": ["50459", "47175", ...],
    "skills": [
        {
            "setName": "Default",
            "skills": [
                {
                    "gems": [
                        {"id": "Metadata/Items/Gems/SkillGemFireball", "level": 20, "quality": 20},
                        ...
                    ]
                }
            ]
        }
    ],
    "items": {...},
    "notes": "Build notes here"
}

Usage:
    python generate_build.py build_spec.json -o output.txt
    python generate_build.py build_spec.json          # stdout (base64 string)
    python generate_build.py build_spec.json --xml    # raw XML to stdout
"""

from __future__ import annotations

import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

from build_codec import encode_build


def _elem(parent: ET.Element, tag: str, text: str | None = None,
           **attrs: str) -> ET.Element:
    """Create a sub-element with optional text and attributes."""
    el = ET.SubElement(parent, tag, **{k: str(v) for k, v in attrs.items()
                                        if v is not None})
    if text is not None:
        el.text = text
    return el


def generate_build_xml(spec: dict) -> str:
    """Generate the Build XML string from a build specification."""
    build = ET.Element("Build")

    # Required attributes
    build.set("className", spec["className"])
    if spec.get("ascendClassName"):
        build.set("ascendClassName", spec["ascendClassName"])
    if spec.get("level"):
        build.set("level", str(spec["level"]))
    if spec.get("mainSocketGroup"):
        build.set("mainSocketGroup", str(spec["mainSocketGroup"]))

    # Passives
    passives = spec.get("passives", [])
    if passives:
        p_el = _elem(build, "Passives", activeVariant="0")
        variant = _elem(p_el, "Variant", name="Default")
        for node_id in passives:
            node = _elem(variant, "Node", id=str(node_id))
            _elem(node, "Stat")  # empty Stat child is required

    # Atlas passives
    atlas = spec.get("atlasPassives", [])
    if atlas:
        a_el = _elem(build, "Atlas", activeVariant="0")
        variant = _elem(a_el, "Variant", name="Default")
        for node_id in atlas:
            node = _elem(variant, "Node", id=str(node_id))
            _elem(node, "Stat")

    # Skills
    skills = spec.get("skills", [])
    if skills:
        s_el = _elem(build, "Skills", activeSkillSet="1")
        for i, skill_set in enumerate(skills):
            ss_el = _elem(
                s_el, "SkillSet",
                title=skill_set.get("setName", f"Set {i + 1}")
            )
            for j, skill in enumerate(skill_set.get("skills", [])):
                sk_el = _elem(
                    ss_el, "Skill",
                    mainActiveSkill=str(skill.get("mainActiveSkill", j + 1)),
                    mainActiveSkillCalcs=str(
                        skill.get("mainActiveSkillCalcs", 1)
                    ),
                )
                for gem in skill.get("gems", []):
                    sk_el.append(_make_gem_element(gem))

    # Items
    items = spec.get("items", {})
    if items:
        i_el = _elem(
            build, "Items",
            activeItemSet=str(items.get("activeItemSet", 1))
        )
        for item in items.get("slots", []):
            el = _elem(
                i_el, "Item",
                id=item.get("id", "")
            )
            el.text = item.get("text", "")

    # Notes
    notes = spec.get("notes", "")
    if notes:
        _elem(build, "Notes", text=notes)

    # Player stats
    for stat in spec.get("stats", []):
        _elem(
            build, "PlayerStat",
            stat=stat["stat"],
            value=str(stat["value"])
        )

    # Buffs
    buffs = spec.get("buffs")
    if buffs:
        _elem(
            build, "Buffs",
            combatList=",".join(buffs.get("combatList", [])),
            buffList=",".join(buffs.get("buffList", [])),
        )

    # Indent the XML for readability
    ET.indent(build, space="  ")
    return ET.tostring(build, encoding="unicode")


def _make_gem_element(gem: dict) -> ET.Element:
    """Create a <Gem> element from a gem spec."""
    el = ET.Element("Gem")
    el.set("gemId", gem["id"])
    if gem.get("level"):
        el.set("level", str(gem["level"]))
    if gem.get("quality"):
        el.set("quality", str(gem["quality"]))
    return el


def generate_build_string(spec: dict) -> str:
    """Generate the full encoded build string from a spec."""
    xml = generate_build_xml(spec)
    return encode_build(xml)


def cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Generate PoE2 GGG build planner file from a spec"
    )
    parser.add_argument("spec", help="Path to build spec JSON file")
    parser.add_argument(
        "-o", "--output",
        help="Output file for encoded build string (default: stdout)"
    )
    parser.add_argument(
        "--xml", action="store_true",
        help="Output raw XML instead of encoded build string"
    )
    args = parser.parse_args()

    spec = json.loads(Path(args.spec).read_text())

    if args.xml:
        result = generate_build_xml(spec)
    else:
        result = generate_build_string(spec)

    if args.output:
        Path(args.output).write_text(result)
    else:
        sys.stdout.write(result)


if __name__ == "__main__":
    cli()
