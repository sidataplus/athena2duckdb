"""Utilities for discovering OMOP Athena vocabulary files."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping


# Known OMOP vocabulary filename -> table name mapping.
KNOWN_TABLES: Mapping[str, str] = {
    "CONCEPT.CSV": "concept",
    "VOCABULARY.CSV": "vocabulary",
    "DOMAIN.CSV": "domain",
    "CONCEPT_CLASS.CSV": "concept_class",
    "RELATIONSHIP.CSV": "relationship",
    "CONCEPT_RELATIONSHIP.CSV": "concept_relationship",
    "CONCEPT_ANCESTOR.CSV": "concept_ancestor",
    "CONCEPT_SYNONYM.CSV": "concept_synonym",
    "DRUG_STRENGTH.CSV": "drug_strength",
    "SOURCE_TO_CONCEPT_MAP.CSV": "source_to_concept_map",
}

EXCLUDED_FILES = {
    "CONCEPT_CPT4.CSV",
    "README.TXT",
}


@dataclass(frozen=True)
class VocabFile:
    """Represents a vocab file and the target DuckDB table name."""

    path: Path
    table_name: str
    canonical_name: str

    @property
    def stem(self) -> str:
        return self.path.stem


def discover_vocab_files(
    directory: Path,
    *,
    suffixes: Iterable[str] | None = (".csv", ".txt"),
) -> list[VocabFile]:
    """Return OMOP vocab files in *directory* mapped to DuckDB table names.

    The lookup is case-insensitive. Known filenames use their curated table
    names; otherwise the filename stem is normalised to snake_case.
    """

    if not directory.exists():
        raise FileNotFoundError(f"Input directory does not exist: {directory}")
    if not directory.is_dir():
        raise NotADirectoryError(f"Input path is not a directory: {directory}")

    suffixes_upper = {suffix.upper() for suffix in suffixes or ()}
    results: list[VocabFile] = []

    for entry in sorted(directory.iterdir()):
        if not entry.is_file():
            continue
        if suffixes_upper and entry.suffix.upper() not in suffixes_upper:
            continue

        canonical_name = entry.name.upper()
        if canonical_name in EXCLUDED_FILES:
            continue
        table_name = KNOWN_TABLES.get(canonical_name)
        if table_name is None:
            continue

        results.append(
            VocabFile(
                path=entry.resolve(),
                table_name=table_name,
                canonical_name=canonical_name,
            )
        )

    return results


def _normalise_to_snake_case(stem: str) -> str:
    """Basic snake_case conversion used for unknown filenames."""

    cleaned = []
    last_was_underscore = False
    for char in stem:
        if char.isalnum():
            cleaned.append(char.lower())
            last_was_underscore = False
        else:
            if not last_was_underscore:
                cleaned.append("_")
                last_was_underscore = True

    value = "".join(cleaned).strip("_")
    return value or stem.lower()
