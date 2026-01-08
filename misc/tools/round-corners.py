#!/usr/bin/env python3
"""
Round Corners - Apply rounded corners to font glyphs

This script processes UFO font files and applies rounded corners to sharp
angles in glyph outlines, creating a "soft" or "rounded" variant of the font.

The algorithm identifies corner points (where segments meet at sharp angles)
and replaces them with smooth bezier curves to create a rounded appearance.

Usage:
  python round-corners.py <input.ufo> <output.ufo> [--radius RADIUS]

Based on the approach used by Open Runde (https://github.com/lauridskern/open-runde)
"""

import argparse
import math
import os
import sys
from typing import List, Tuple, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from defcon import Font, Glyph, Contour, Point


def normalize(v: Tuple[float, float]) -> Tuple[float, float]:
    """Normalize a 2D vector to unit length."""
    length = math.sqrt(v[0] * v[0] + v[1] * v[1])
    if length == 0:
        return (0.0, 0.0)
    return (v[0] / length, v[1] / length)


def dot(v1: Tuple[float, float], v2: Tuple[float, float]) -> float:
    """Calculate dot product of two 2D vectors."""
    return v1[0] * v2[0] + v1[1] * v2[1]


def distance(p1: Tuple[float, float], p2: Tuple[float, float]) -> float:
    """Calculate distance between two points."""
    dx = p2[0] - p1[0]
    dy = p2[1] - p1[1]
    return math.sqrt(dx * dx + dy * dy)


def angle_between_vectors(v1: Tuple[float, float], v2: Tuple[float, float]) -> float:
    """Calculate angle between two vectors in radians."""
    n1 = normalize(v1)
    n2 = normalize(v2)
    d = dot(n1, n2)
    # Clamp to avoid floating point errors
    d = max(-1.0, min(1.0, d))
    return math.acos(d)


def is_corner_point(point: Point) -> bool:
    """Check if a point is a corner (non-smooth) point."""
    # In UFO/defcon, smooth points have 'smooth' attribute set to True
    # Corner points are on-curve points that are not smooth
    if point.segmentType is None:  # off-curve point
        return False
    return not getattr(point, 'smooth', False)


def get_incoming_direction(contour: Contour, point_index: int) -> Optional[Tuple[float, float]]:
    """Get the incoming direction vector at a point."""
    points = list(contour)
    n = len(points)
    if n < 2:
        return None

    current = points[point_index]

    # Look backwards for the previous defining point
    prev_index = (point_index - 1) % n
    prev_point = points[prev_index]

    # If the previous point is off-curve, use it for direction
    # Otherwise, use the previous on-curve point
    if prev_point.segmentType is None:
        # Off-curve point - direction comes from there
        return (current.x - prev_point.x, current.y - prev_point.y)
    else:
        # On-curve point - straight line
        return (current.x - prev_point.x, current.y - prev_point.y)


def get_outgoing_direction(contour: Contour, point_index: int) -> Optional[Tuple[float, float]]:
    """Get the outgoing direction vector at a point."""
    points = list(contour)
    n = len(points)
    if n < 2:
        return None

    current = points[point_index]

    # Look forward for the next defining point
    next_index = (point_index + 1) % n
    next_point = points[next_index]

    # If the next point is off-curve, use it for direction
    # Otherwise, use the next on-curve point
    if next_point.segmentType is None:
        # Off-curve point - direction goes there
        return (next_point.x - current.x, next_point.y - current.y)
    else:
        # On-curve point - straight line
        return (next_point.x - current.x, next_point.y - current.y)


def round_corner(
    contour: Contour,
    point_index: int,
    radius: float,
    min_angle: float = 0.1
) -> Optional[List[Point]]:
    """
    Round a corner at the specified point index.

    Returns a list of points that should replace the corner point,
    or None if the corner cannot/should not be rounded.

    Args:
        contour: The contour containing the point
        point_index: Index of the corner point
        radius: Rounding radius in font units
        min_angle: Minimum angle (in radians) to consider for rounding
    """
    points = list(contour)
    n = len(points)

    if n < 3:
        return None

    current = points[point_index]

    # Only round on-curve corner points
    if current.segmentType is None or getattr(current, 'smooth', False):
        return None

    in_dir = get_incoming_direction(contour, point_index)
    out_dir = get_outgoing_direction(contour, point_index)

    if in_dir is None or out_dir is None:
        return None

    # Normalize directions
    in_norm = normalize(in_dir)
    out_norm = normalize(out_dir)

    # Check if directions are valid
    if in_norm == (0.0, 0.0) or out_norm == (0.0, 0.0):
        return None

    # Calculate angle between incoming and outgoing directions
    # For corners, the incoming direction should be reversed to measure the actual corner angle
    in_reversed = (-in_norm[0], -in_norm[1])
    angle = angle_between_vectors(in_reversed, out_norm)

    # Skip if angle is too small (nearly straight) or too large (nearly 180 degrees)
    if angle < min_angle or angle > math.pi - min_angle:
        return None

    # Calculate the half angle for arc construction
    half_angle = angle / 2.0

    # Calculate tangent length based on radius and angle
    # The distance to move back from corner along each edge
    tan_length = radius / math.tan(half_angle) if half_angle > 0.01 else radius * 10

    # Calculate the control point handle length
    # For a bezier curve approximating an arc of angle θ:
    # handle_length = (4/3) * tan(θ/4) * radius
    arc_angle = math.pi - angle  # The arc spans this angle
    handle_length = (4.0 / 3.0) * math.tan(arc_angle / 4.0) * radius

    # Find the previous and next on-curve points for distance checking
    prev_index = (point_index - 1) % n
    next_index = (point_index + 1) % n

    # Get actual previous and next points (may be off-curve)
    prev_point = points[prev_index]
    next_point = points[next_index]

    # Find distances to limit the rounding
    # For incoming edge
    if prev_point.segmentType is None:
        # Previous is off-curve, find the on-curve before it
        prev_oncurve_idx = (prev_index - 1) % n
        while points[prev_oncurve_idx].segmentType is None and prev_oncurve_idx != point_index:
            prev_oncurve_idx = (prev_oncurve_idx - 1) % n
        in_dist = distance((current.x, current.y), (points[prev_oncurve_idx].x, points[prev_oncurve_idx].y))
    else:
        in_dist = distance((current.x, current.y), (prev_point.x, prev_point.y))

    # For outgoing edge
    if next_point.segmentType is None:
        # Next is off-curve, find the on-curve after it
        next_oncurve_idx = (next_index + 1) % n
        while points[next_oncurve_idx].segmentType is None and next_oncurve_idx != point_index:
            next_oncurve_idx = (next_oncurve_idx + 1) % n
        out_dist = distance((current.x, current.y), (points[next_oncurve_idx].x, points[next_oncurve_idx].y))
    else:
        out_dist = distance((current.x, current.y), (next_point.x, next_point.y))

    # Limit the tangent length to not exceed half the edge length
    max_tan = min(in_dist, out_dist) * 0.4
    if tan_length > max_tan:
        # Scale down the radius proportionally
        scale = max_tan / tan_length
        tan_length = max_tan
        handle_length *= scale

    # Calculate the new points
    # Start point: move back from corner along incoming edge
    start_x = current.x - in_norm[0] * tan_length
    start_y = current.y - in_norm[1] * tan_length

    # End point: move forward from corner along outgoing edge
    end_x = current.x + out_norm[0] * tan_length
    end_y = current.y + out_norm[1] * tan_length

    # Control point 1: from start point, in the direction of the corner
    cp1_x = start_x + in_norm[0] * handle_length
    cp1_y = start_y + in_norm[1] * handle_length

    # Control point 2: from end point, in the direction of the corner (reversed)
    cp2_x = end_x - out_norm[0] * handle_length
    cp2_y = end_y - out_norm[1] * handle_length

    # Create the new points using proper Point constructor
    new_points = []

    # Start point (on-curve, smooth)
    start_pt = Point((round(start_x), round(start_y)), segmentType='curve', smooth=True)
    new_points.append(start_pt)

    # Control point 1 (off-curve)
    cp1 = Point((round(cp1_x), round(cp1_y)), segmentType=None, smooth=False)
    new_points.append(cp1)

    # Control point 2 (off-curve)
    cp2 = Point((round(cp2_x), round(cp2_y)), segmentType=None, smooth=False)
    new_points.append(cp2)

    # End point (on-curve, smooth)
    end_pt = Point((round(end_x), round(end_y)), segmentType='curve', smooth=True)
    new_points.append(end_pt)

    return new_points


def process_contour(contour: Contour, radius: float) -> Contour:
    """Process a contour, rounding all eligible corners."""
    points = list(contour)
    n = len(points)

    if n < 3:
        return contour

    # Find all corner points that need rounding
    corners_to_round = []
    for i, point in enumerate(points):
        if is_corner_point(point):
            corners_to_round.append(i)

    if not corners_to_round:
        return contour

    # Process corners from end to beginning to avoid index shifting issues
    new_points = list(points)

    for corner_idx in reversed(corners_to_round):
        # Create a temporary contour with current state
        temp_contour = Contour()
        for p in new_points:
            temp_contour.appendPoint(Point((p.x, p.y), segmentType=p.segmentType, smooth=getattr(p, 'smooth', False)))

        replacement = round_corner(temp_contour, corner_idx, radius)
        if replacement:
            # Replace the corner point with the new points
            new_points = new_points[:corner_idx] + replacement + new_points[corner_idx + 1:]

    # Create the new contour
    result = Contour()
    for p in new_points:
        result.appendPoint(Point((p.x, p.y), segmentType=p.segmentType, smooth=getattr(p, 'smooth', False)))

    return result


def process_glyph(glyph: Glyph, radius: float) -> None:
    """Process all contours in a glyph."""
    # Skip glyphs that are only components (no contours)
    # In defcon, iterate over glyph to get contours; use len() to check count
    if len(glyph) == 0:
        return

    # Process each contour
    new_contours = []
    for contour in glyph:
        new_contour = process_contour(contour, radius)
        new_contours.append(new_contour)

    # Clear existing contours and add processed ones
    glyph.clearContours()
    for contour in new_contours:
        new_c = glyph.instantiateContour()
        for point in contour:
            new_c.appendPoint(Point((point.x, point.y), segmentType=point.segmentType, smooth=getattr(point, 'smooth', False)))
        glyph.appendContour(new_c)


def process_ufo(input_path: str, output_path: str, radius: float, verbose: bool = False) -> None:
    """Process a UFO file, rounding corners in all glyphs."""
    if verbose:
        print(f"Loading {input_path}...")

    font = Font(input_path)

    # Update font info for the rounded variant
    family_name = font.info.familyName or "Inter"
    if "Rounded" not in family_name:
        font.info.familyName = family_name + " Rounded"

    style_name = font.info.styleName or ""
    font.info.postscriptFontName = (font.info.familyName + "-" + style_name).replace(" ", "")

    if verbose:
        print(f"Processing {len(font)} glyphs with radius {radius}...")

    processed = 0
    for glyph in font:
        # Check if glyph has contours (len(glyph) gives number of contours)
        if len(glyph) > 0:
            process_glyph(glyph, radius)
            processed += 1

    if verbose:
        print(f"Processed {processed} glyphs with contours")

    # Save the modified font
    if verbose:
        print(f"Saving to {output_path}...")

    font.save(output_path)

    if verbose:
        print("Done!")


def main():
    parser = argparse.ArgumentParser(
        description="Apply rounded corners to font glyphs in UFO format"
    )
    parser.add_argument(
        "input",
        help="Input UFO file path"
    )
    parser.add_argument(
        "output",
        help="Output UFO file path"
    )
    parser.add_argument(
        "--radius", "-r",
        type=float,
        default=30.0,
        help="Rounding radius in font units (default: 30)"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose output"
    )

    args = parser.parse_args()

    if not os.path.exists(args.input):
        print(f"Error: Input file not found: {args.input}", file=sys.stderr)
        sys.exit(1)

    process_ufo(args.input, args.output, args.radius, args.verbose)


if __name__ == "__main__":
    main()
