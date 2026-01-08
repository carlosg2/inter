#!/usr/bin/env python3
"""
Generate Designspace for Inter Rounded Variable Font

This script creates a designspace file for building Inter Rounded as a variable font
with two axes:
  - Weight (wght): 400-700 (Regular to Bold)
  - Rounding (ROND): 0-100 (No rounding to full rounding)

The rounding axis allows users to control the corner rounding amount continuously.

Usage:
  python gen-rounded-designspace.py <base_designspace> <output_designspace> [options]

Example:
  python gen-rounded-designspace.py build/ufo/Inter-Roman.designspace \
      build/ufo-rounded/InterRounded.designspace --radius-max 50
"""

import argparse
import os
import sys
import shutil
from fontTools.designspaceLib import (
    DesignSpaceDocument, 
    AxisDescriptor, 
    SourceDescriptor, 
    InstanceDescriptor
)

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# Default family name for the rounded variant
DEFAULT_FAMILY_NAME = "Inter Rounded"


def create_rounded_designspace(
    base_designspace_path: str,
    output_designspace_path: str,
    rounded_ufo_dir: str,
    radius_max: float = 50.0,
    family_name: str = DEFAULT_FAMILY_NAME,
    verbose: bool = False
):
    """
    Create a designspace for Inter Rounded variable font.
    
    Args:
        base_designspace_path: Path to the base Inter designspace
        output_designspace_path: Output path for the rounded designspace
        rounded_ufo_dir: Directory containing rounded UFOs
        radius_max: Maximum rounding radius (maps to ROND=100)
        family_name: Family name for the rounded font
        verbose: Enable verbose output
    """
    if verbose:
        print(f"Loading base designspace: {base_designspace_path}")
    
    # Load base designspace to understand the weight axis structure
    base_doc = DesignSpaceDocument.fromfile(base_designspace_path)
    
    # Create new designspace
    doc = DesignSpaceDocument()
    
    # Find the weight axis from base designspace
    base_wght_axis = None
    for axis in base_doc.axes:
        if axis.tag == "wght":
            base_wght_axis = axis
            break
    
    if not base_wght_axis:
        raise ValueError("Could not find weight axis in base designspace")
    
    # Add Weight axis (limited to Regular-Bold range like Open Runde)
    wght_axis = AxisDescriptor()
    wght_axis.tag = "wght"
    wght_axis.name = "Weight"
    wght_axis.minimum = 400
    wght_axis.default = 400
    wght_axis.maximum = 700
    wght_axis.labelNames = {"en": "Weight"}
    doc.addAxis(wght_axis)
    
    # Add Rounding axis (custom axis for corner rounding)
    rond_axis = AxisDescriptor()
    rond_axis.tag = "ROND"  # Custom axis tag (uppercase = private/custom)
    rond_axis.name = "Rounding"
    rond_axis.minimum = 0
    rond_axis.default = 100  # Default to fully rounded
    rond_axis.maximum = 100
    rond_axis.labelNames = {"en": "Rounding"}
    doc.addAxis(rond_axis)
    
    # Weight values we support (matching Open Runde)
    weights = [
        ("Regular", 400),
        ("Medium", 500),
        ("SemiBold", 600),
        ("Bold", 700),
    ]
    
    # Rounding values (0 = no rounding, 100 = full rounding)
    # We need sources at both ends of the rounding axis for each weight
    rounding_values = [
        (0, "Sharp"),      # No rounding (original Inter)
        (100, "Rounded"),  # Full rounding
    ]
    
    # Add sources for each weight and rounding combination
    sources_added = []
    for weight_name, weight_value in weights:
        for rond_value, rond_suffix in rounding_values:
            source = SourceDescriptor()
            
            if rond_value == 0:
                # Sharp version - use original Inter UFO
                source.path = os.path.join(
                    os.path.dirname(base_designspace_path),
                    f"Inter-{weight_name}.ufo"
                )
                source.familyName = family_name
            else:
                # Rounded version - use rounded UFO
                source.path = os.path.join(
                    rounded_ufo_dir,
                    f"Inter-{weight_name}.ufo"
                )
                source.familyName = family_name
            
            source.name = f"Inter {weight_name} {rond_suffix}"
            source.styleName = f"{weight_name} {rond_suffix}"
            source.location = {"Weight": weight_value, "Rounding": rond_value}
            
            # Set the default source (Regular Rounded)
            if weight_value == 400 and rond_value == 100:
                source.copyLib = True
                source.copyInfo = True
                source.copyGroups = True
                source.copyFeatures = True
            
            doc.addSource(source)
            sources_added.append(source.name)
            
            if verbose:
                print(f"  Added source: {source.name} at wght={weight_value}, ROND={rond_value}")
    
    # Add instances for common use cases
    instances = [
        ("Regular", 400, 100),
        ("Medium", 500, 100),
        ("SemiBold", 600, 100),
        ("Bold", 700, 100),
    ]
    
    ps_family_name = family_name.replace(" ", "")
    
    for style_name, weight, rounding in instances:
        instance = InstanceDescriptor()
        instance.name = f"{family_name} {style_name}"
        instance.familyName = family_name
        instance.styleName = style_name
        instance.location = {"Weight": weight, "Rounding": rounding}
        instance.postScriptFontName = f"{ps_family_name}-{style_name}".replace(" ", "")
        instance.styleMapFamilyName = family_name
        
        # Set style map style name based on weight
        if weight == 700:
            instance.styleMapStyleName = "bold"
        else:
            instance.styleMapStyleName = "regular"
        
        doc.addInstance(instance)
        
        if verbose:
            print(f"  Added instance: {instance.name}")
    
    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_designspace_path), exist_ok=True)
    
    # Write the designspace
    doc.write(output_designspace_path)
    
    if verbose:
        print(f"Written designspace to: {output_designspace_path}")
        print(f"Total sources: {len(doc.sources)}")
        print(f"Total instances: {len(doc.instances)}")
    
    return doc


def main():
    parser = argparse.ArgumentParser(
        description="Generate designspace for Inter Rounded variable font"
    )
    parser.add_argument(
        "base_designspace",
        help="Path to base Inter designspace file"
    )
    parser.add_argument(
        "output_designspace",
        help="Output path for rounded designspace"
    )
    parser.add_argument(
        "--rounded-ufo-dir", "-d",
        default="build/ufo-rounded",
        help="Directory containing rounded UFOs (default: build/ufo-rounded)"
    )
    parser.add_argument(
        "--radius-max", "-r",
        type=float,
        default=50.0,
        help="Maximum rounding radius in font units (default: 50)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.base_designspace):
        print(f"Error: Base designspace not found: {args.base_designspace}", file=sys.stderr)
        sys.exit(1)
    
    create_rounded_designspace(
        args.base_designspace,
        args.output_designspace,
        args.rounded_ufo_dir,
        args.radius_max,
        args.verbose
    )


if __name__ == "__main__":
    main()
