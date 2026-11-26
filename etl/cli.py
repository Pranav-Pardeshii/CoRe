"""Unified CLI entrypoint for the CoRe ETL pipeline."""

from __future__ import annotations

import argparse
import logging
from collections.abc import Sequence
from pathlib import Path

from etl.config import DEFAULT_CSV_PATH, DEFAULT_OUTPUT_DIR, DEFAULT_PDF_DIR
from etl.extract import extract_all
from etl.load import DEFAULT_BATCH_SIZE, load_csv_to_db
from etl.transform import transform_csvs
from etl.validate import ValidationError, format_validation_summary, validate_csv

logger = logging.getLogger(__name__)


def build_parser() -> argparse.ArgumentParser:
    """Construct the CLI argument parser for ``python -m etl``."""
    parser = argparse.ArgumentParser(
        prog="python -m etl",
        description="CoRe MHT-CET ETL pipeline (extract, transform, validate, load).",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    extract_parser = subparsers.add_parser("extract", help="Extract PDFs into per-round CSVs.")
    extract_parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    extract_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)

    transform_parser = subparsers.add_parser(
        "transform", help="Normalize, map divisions, and deduplicate per-round CSVs."
    )
    transform_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    transform_parser.add_argument("--csv-path", type=Path, default=DEFAULT_CSV_PATH)

    validate_parser = subparsers.add_parser(
        "validate", help="Run strict pre-load validation on the flat CSV."
    )
    validate_parser.add_argument("--csv-path", type=Path, default=DEFAULT_CSV_PATH)

    load_parser = subparsers.add_parser("load", help="Validate and load flat CSV into MySQL.")
    load_parser.add_argument("--csv-path", type=Path, default=DEFAULT_CSV_PATH)
    load_parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    load_parser.add_argument("--dry-run", action="store_true")

    run_parser = subparsers.add_parser(
        "run", help="Run full end-to-end ETL (extract -> transform -> validate -> load)."
    )
    run_parser.add_argument("--pdf-dir", type=Path, default=DEFAULT_PDF_DIR)
    run_parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    run_parser.add_argument("--csv-path", type=Path, default=DEFAULT_CSV_PATH)
    run_parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    run_parser.add_argument("--dry-run", action="store_true")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Execute the CoRe ETL CLI and return a process exit code."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    try:
        if args.command == "extract":
            extract_all(pdf_dir=args.pdf_dir, output_dir=args.output_dir)
        elif args.command == "transform":
            transform_csvs(input_dir=args.output_dir, output_csv=args.csv_path)
        elif args.command == "validate":
            report = validate_csv(args.csv_path)
            print(format_validation_summary(report))
        elif args.command == "load":
            load_csv_to_db(
                args.csv_path,
                batch_size=args.batch_size,
                dry_run=args.dry_run,
            )
        elif args.command == "run":
            extract_all(pdf_dir=args.pdf_dir, output_dir=args.output_dir)
            transform_csvs(input_dir=args.output_dir, output_csv=args.csv_path)
            report = validate_csv(args.csv_path)
            print(format_validation_summary(report))
            load_csv_to_db(
                args.csv_path,
                batch_size=args.batch_size,
                dry_run=args.dry_run,
                skip_validation=True,
            )
    except ValidationError as exc:
        print(format_validation_summary(exc.report))
        logger.error("ETL aborted due to validation failure.")
        return 1
    except Exception as exc:
        logger.error("ETL failed: %s", exc)
        return 1

    return 0
