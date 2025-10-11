"""Command-line interface for loading OMOP Athena vocabularies into DuckDB."""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path
from typing import Sequence

from .loader import CSVOptions, LoadSummary, load_vocab_dir, verify_row_counts


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="athena2duckdb",
        description="Load OMOP Athena vocabulary CSV/TSV files into a DuckDB database",
    )
    parser.add_argument(
        "input_dir",
        help="Path to the directory containing Athena vocabulary files",
    )
    parser.add_argument(
        "-o",
        "--out",
        default="omop_vocab.duckdb",
        help="Destination DuckDB database file (default: %(default)s)",
    )
    parser.add_argument(
        "--sep",
        default="\t",
        help="Field delimiter used by the input files (default: tab)",
    )
    parser.add_argument(
        "--encoding",
        default="UTF-8",
        help="File encoding passed to DuckDB read_csv (default: UTF-8)",
    )
    parser.add_argument(
        "--threads",
        type=int,
        help="Number of DuckDB execution threads (default: auto)",
    )
    parser.add_argument(
        "--schema",
        default="main",
        help="Target DuckDB schema for created tables (default: main)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace an existing DuckDB file instead of failing",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging",
    )

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=logging.INFO if args.verbose else logging.WARNING,
        format="%(levelname)s: %(message)s",
    )
    logger = logging.getLogger("athena2duckdb.cli")

    csv_options = CSVOptions(
        sep=args.sep,
        encoding=args.encoding,
    )

    progress = _ProgressBar()

    try:
        summary = load_vocab_dir(
            Path(args.input_dir),
            Path(args.out),
            csv_options=csv_options,
            overwrite=args.overwrite,
            threads=args.threads,
            logger=logger,
            progress_callback=progress.update,
            schema=args.schema,
        )
    except Exception as exc:  # noqa: BLE001 - surface clean CLI failures
        logger.error(str(exc))
        progress.finish(force_newline=True)
        return 1

    progress.finish()

    _print_load_summary(summary)

    results = verify_row_counts(
        summary.db_path,
        summary.vocab_files,
        csv_options=csv_options,
        threads=args.threads,
        schema=summary.schema,
    )

    mismatches = [result for result in results if not result.matches]

    for result in results:
        status = "OK" if result.matches else "MISMATCH"
        print(
            f"{status:9s} table={result.table_name:<25s} "
            f"csv_rows={result.csv_rows:,} table_rows={result.table_rows:,}"
        )

    if mismatches:
        logger.error(
            "Row count mismatches detected for %d tables.",
            len(mismatches),
        )
        return 2

    return 0


def _print_load_summary(summary: LoadSummary) -> None:
    table_count = len(summary.vocab_files)
    tables = ", ".join(sorted({v.table_name for v in summary.vocab_files}))
    print(
        f"Loaded {table_count} tables into {summary.db_path} (schema {summary.schema}).\n"
        f"Tables: {tables}"
    )


class _ProgressBar:
    def __init__(self) -> None:
        self._total: int | None = None
        self._current: int = 0
        self._last_line_length: int = 0
        self._finished: bool = False

    def update(self, current: int, vocab_file, total: int) -> None:
        if self._finished:
            return

        self._total = total
        self._current = current

        table_name = getattr(vocab_file, "table_name", "")
        bar = self._render_bar(current, total)
        line = f"\rLoading {bar} {current}/{total} {table_name}"

        padding = " " * max(self._last_line_length - len(line), 0)
        sys.stdout.write(line + padding)
        sys.stdout.flush()
        self._last_line_length = len(line)

    def _render_bar(self, current: int, total: int) -> str:
        width = 30
        filled = int(width * current / total)
        return f"[{ '#' * filled }{ '-' * (width - filled) }]"

    def finish(self, force_newline: bool = False) -> None:
        if self._finished:
            return
        self._finished = True

        if self._total is None:
            if force_newline:
                sys.stdout.write("\n")
                sys.stdout.flush()
            return

        bar = self._render_bar(self._total, self._total)
        line = f"\rLoading {bar} {self._total}/{self._total}"
        padding = " " * max(self._last_line_length - len(line), 0)
        sys.stdout.write(line + padding + "\n")
        sys.stdout.flush()


if __name__ == "__main__":  # pragma: no cover - CLI entry-point guard
    sys.exit(main())
