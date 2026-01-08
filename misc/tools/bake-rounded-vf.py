#!/usr/bin/env python3
"""
Bake the final Inter Rounded variable font.

This script performs the following:
  1. Renames the family to "Inter Rounded Variable"
  2. Builds a STAT table with Weight and Rounding axes
  3. Updates font metadata

Based on bake-vf.py for the main Inter variable font.
"""
import sys
import os
import argparse
from fontTools.ttLib import TTFont
from fontTools.otlLib.builder import buildStatTable

FLAG_DEFAULT = 0x2  # elidable value, marks a location as default


def stat_axes(rond_min=0, rond_max=100):
    """Build STAT table axes configuration.
    
    Args:
        rond_min: Minimum value of the ROND axis
        rond_max: Maximum value of the ROND axis
    """
    return [
        dict(name="Weight", tag="wght", ordering=0, values=[
            dict(nominalValue=400, rangeMinValue=400, rangeMaxValue=450, name="Regular",
                 flags=FLAG_DEFAULT, linkedValue=700),
            dict(nominalValue=500, rangeMinValue=450, rangeMaxValue=550, name="Medium"),
            dict(nominalValue=600, rangeMinValue=550, rangeMaxValue=650, name="SemiBold"),
            dict(nominalValue=700, rangeMinValue=650, rangeMaxValue=700, name="Bold"),
        ]),
        dict(name="Rounding", tag="ROND", ordering=1, values=[
            dict(nominalValue=rond_min, rangeMinValue=rond_min, rangeMaxValue=50,
                 name="Sharp"),
            dict(nominalValue=rond_max, rangeMinValue=50, rangeMaxValue=rond_max,
                 name="Rounded", flags=FLAG_DEFAULT),
        ]),
    ]


def update_name_table(font, family_name="Inter Rounded"):
    """Update the name table for the rounded variable font."""
    name_table = font["name"]
    
    # Name IDs to update
    # 1 = Family name
    # 4 = Full name
    # 6 = PostScript name
    # 16 = Typographic Family name
    # 21 = WWS Family name
    # 25 = Variations PostScript Name Prefix
    
    for record in name_table.names:
        if record.nameID == 1:  # Family name
            name_table.setName(family_name, 1, record.platformID, record.platEncID, record.langID)
        elif record.nameID == 4:  # Full name
            style = ""
            for r in name_table.names:
                if r.nameID == 2 and r.platformID == record.platformID:
                    try:
                        style = r.toUnicode()
                    except (UnicodeDecodeError, AttributeError):
                        pass
                    break
            full_name = f"{family_name} {style}".strip()
            name_table.setName(full_name, 4, record.platformID, record.platEncID, record.langID)
        elif record.nameID == 6:  # PostScript name
            ps_name = family_name.replace(" ", "") + "-Regular"
            name_table.setName(ps_name, 6, record.platformID, record.platEncID, record.langID)
        elif record.nameID == 16:  # Typographic Family name
            name_table.setName(family_name, 16, record.platformID, record.platEncID, record.langID)
        elif record.nameID == 21:  # WWS Family name
            name_table.setName(family_name, 21, record.platformID, record.platEncID, record.langID)
        elif record.nameID == 25:  # Variations PostScript Name Prefix
            ps_prefix = family_name.replace(" ", "")
            name_table.setName(ps_prefix, 25, record.platformID, record.platEncID, record.langID)


def main():
    parser = argparse.ArgumentParser(
        description="Bake the final Inter Rounded variable font"
    )
    parser.add_argument(
        "input",
        help="Input variable font file"
    )
    parser.add_argument(
        "-o", "--output",
        required=True,
        help="Output variable font file"
    )
    parser.add_argument(
        "--family-name",
        default="Inter Rounded",
        help="Family name (default: Inter Rounded)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        print(f"Loading font: {args.input}")
    
    font = TTFont(args.input)
    
    # Get ROND axis range from fvar
    rond_min = 0
    rond_max = 100
    if "fvar" in font:
        for axis in font["fvar"].axes:
            if axis.axisTag == "ROND":
                rond_min = axis.minValue
                rond_max = axis.maxValue
                break
    
    if args.verbose:
        print(f"ROND axis range: {rond_min} - {rond_max}")
    
    # Update name table
    if args.verbose:
        print(f"Updating name table with family name: {args.family_name}")
    update_name_table(font, args.family_name)
    
    # Build STAT table
    if args.verbose:
        print("Building STAT table")
    buildStatTable(font, stat_axes(rond_min, rond_max))
    
    # Save the font
    if args.verbose:
        print(f"Saving to: {args.output}")
    
    os.makedirs(os.path.dirname(args.output) or ".", exist_ok=True)
    font.save(args.output)
    
    if args.verbose:
        print("Done!")


if __name__ == "__main__":
    main()
