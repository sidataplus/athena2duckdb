"""Public package API for athena2duckdb."""

from .cli import main
from .loader import (
    CSVOptions,
    LoadSummary,
    RowCountResult,
    load_vocab_dir,
    verify_row_counts,
)
from .tables import VocabFile, discover_vocab_files

__all__ = [
    "CSVOptions",
    "LoadSummary",
    "RowCountResult",
    "VocabFile",
    "discover_vocab_files",
    "load_vocab_dir",
    "main",
    "verify_row_counts",
]
