"""CLI entry point for river ksn calculation."""

import argparse
import logging
import sys

from river_ksn.pipeline import run_pipeline


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        description="Calculate river normalized steepness index (ksn) from DEM",
    )
    parser.add_argument(
        "input",
        help="Path to input DEM GeoTIFF file",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="./output",
        help="Output directory (default: ./output)",
    )
    parser.add_argument(
        "--theta",
        type=float,
        default=None,
        help="Reference concavity index (auto-calibrated if omitted)",
    )
    parser.add_argument(
        "--threshold",
        type=float,
        default=None,
        help="Flow accumulation threshold for channel definition (auto if omitted)",
    )
    parser.add_argument(
        "--intermediate",
        action="store_true",
        help="Export intermediate rasters (filled DEM, flow accumulation, slope)",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress progress messages",
    )

    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.WARNING if args.quiet else logging.INFO,
        format="%(levelname)s: %(message)s",
    )

    run_pipeline(
        input_path=args.input,
        output_dir=args.output,
        theta=args.theta,
        threshold=args.threshold,
        intermediate=args.intermediate,
    )


if __name__ == "__main__":
    main()
