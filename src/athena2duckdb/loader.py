"""Loading OMOP Athena vocabulary exports into DuckDB."""

from __future__ import annotations

from dataclasses import dataclass
import logging
from pathlib import Path
from typing import Callable, Iterable, Sequence

import duckdb

from .schema import TABLE_DEFINITIONS, ColumnDefinition, IndexDefinition, TableDefinition
from .tables import VocabFile, discover_vocab_files

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class CSVOptions:
    """DuckDB CSV reader options controlling ingestion behaviour."""

    sep: str = "\t"
    header: bool = True
    quote: str = ""
    escape: str = ""
    nullstr: str = ""
    all_varchar: bool = True
    encoding: str = "UTF-8"


@dataclass(frozen=True)
class LoadSummary:
    """Details about a successful vocabulary load."""

    db_path: Path
    vocab_files: Sequence[VocabFile]
    schema: str


@dataclass(frozen=True)
class RowCountResult:
    """Comparison between CSV source rows and loaded table rows."""

    table_name: str
    csv_rows: int
    table_rows: int
    path: Path

    @property
    def matches(self) -> bool:
        return self.csv_rows == self.table_rows


def load_vocab_dir(
    input_dir: Path | str,
    db_path: Path | str,
    *,
    csv_options: CSVOptions | None = None,
    overwrite: bool = False,
    threads: int | None = None,
    logger: logging.Logger | None = None,
    progress_callback: Callable[[int, VocabFile, int], None] | None = None,
    schema: str = "main",
) -> LoadSummary:
    """Load all recognised OMOP vocabulary files from *input_dir* into DuckDB.

    Parameters
    ----------
    input_dir:
        Directory containing the extracted Athena vocabulary CSV/TSV files.
    db_path:
        Destination DuckDB database file.
    csv_options:
        Reader options forwarded to DuckDB's ``read_csv``.
    overwrite:
        If True, delete an existing database before loading.
    threads:
        If provided, sets ``PRAGMA threads`` for the DuckDB connection.
    logger:
        Optional logger override. Defaults to module logger.

    Returns
    -------
    LoadSummary
        Summary containing the database path and loaded file metadata.
    """

    csv_options = csv_options or CSVOptions()
    logger = logger or LOGGER

    input_path = Path(input_dir)
    db_file = Path(db_path)

    vocab_files = discover_vocab_files(input_path)
    if not vocab_files:
        raise ValueError(
            f"No OMOP vocabulary files were found in {input_path}. "
            "Expected files like CONCEPT.csv, VOCABULARY.csv, etc."
        )

    if db_file.exists():
        if overwrite:
            logger.info("Removing existing database at %s", db_file)
            db_file.unlink()
        else:
            raise FileExistsError(
                f"DuckDB file {db_file} already exists. Use --overwrite to replace it."
            )

    db_file.parent.mkdir(parents=True, exist_ok=True)

    logger.info("Loading %d vocab files into %s", len(vocab_files), db_file)

    conn = duckdb.connect(str(db_file))
    try:
        if threads is not None:
            conn.execute(f"PRAGMA threads={int(threads)}")

        schema_identifier = _escape_identifier(schema)
        conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema_identifier}")

        total = len(vocab_files)
        for index, vocab in enumerate(vocab_files, start=1):
            _load_single_file(
                conn,
                vocab,
                csv_options,
                logger,
                schema,
            )
            if progress_callback is not None:
                progress_callback(index, vocab, total)

        conn.execute("CHECKPOINT")
    finally:
        conn.close()

    return LoadSummary(db_path=db_file, vocab_files=vocab_files, schema=schema)


def _load_single_file(
    conn: duckdb.DuckDBPyConnection,
    vocab: VocabFile,
    csv_options: CSVOptions,
    logger: logging.Logger,
    schema: str,
) -> None:
    definition = TABLE_DEFINITIONS.get(vocab.table_name)

    if definition is not None:
        logger.debug(
            "Loading typed table %s from %s",
            vocab.table_name,
            vocab.path,
        )
        _load_typed_table(conn, vocab, definition, csv_options, schema)
        return

    logger.debug("Loading fallback table %s from %s", vocab.table_name, vocab.path)
    _load_varchar_table(conn, vocab, csv_options, schema)


def verify_row_counts(
    db_path: Path | str,
    vocab_files: Iterable[VocabFile],
    csv_options: CSVOptions | None = None,
    *,
    threads: int | None = None,
    schema: str = "main",
) -> list[RowCountResult]:
    """Compare CSV row counts with the corresponding DuckDB tables."""

    csv_options = csv_options or CSVOptions()
    db_file = Path(db_path)

    if not db_file.exists():
        raise FileNotFoundError(f"DuckDB file does not exist: {db_file}")

    results: list[RowCountResult] = []

    conn = duckdb.connect(str(db_file), read_only=True)
    try:
        if threads is not None:
            conn.execute(f"PRAGMA threads={int(threads)}")

        for vocab in vocab_files:
            csv_rows = _count_csv_rows(conn, vocab.path, csv_options)
            table_rows = _count_table_rows(conn, schema, vocab.table_name)
            results.append(
                RowCountResult(
                    table_name=vocab.table_name,
                    csv_rows=csv_rows,
                    table_rows=table_rows,
                    path=vocab.path,
                )
            )
    finally:
        conn.close()

    return results


def _count_csv_rows(
    conn: duckdb.DuckDBPyConnection,
    path: Path,
    csv_options: CSVOptions,
) -> int:
    sql = (
        "SELECT COUNT(*) FROM read_csv(\n"
        "    ?,\n"
        f"    { _csv_options_sql(csv_options) }\n"
        ")"
    )
    return conn.execute(sql, [str(path)]).fetchone()[0]


def _count_table_rows(conn: duckdb.DuckDBPyConnection, schema: str, table_name: str) -> int:
    qualified = _qualified_table(schema, table_name)
    return conn.execute(f"SELECT COUNT(*) FROM {qualified}").fetchone()[0]


def _csv_options_sql(csv_options: CSVOptions) -> str:
    parts: list[str] = []

    parts.append(f"sep={_sql_literal(csv_options.sep)}")
    parts.append(f"header={'true' if csv_options.header else 'false'}")
    parts.append(f"quote={_sql_literal(csv_options.quote)}")
    parts.append(f"escape={_sql_literal(csv_options.escape)}")
    parts.append(f"nullstr={_sql_literal(csv_options.nullstr)}")
    parts.append(f"all_varchar={'true' if csv_options.all_varchar else 'false'}")
    parts.append(f"encoding={_sql_literal(csv_options.encoding)}")

    return ",\n    ".join(parts)


def _sql_literal(value: str | None) -> str:
    if value is None:
        return "NULL"
    escaped = value.replace("'", "''")
    return f"'{escaped}'"


def _escape_identifier(identifier: str) -> str:
    escaped = identifier.replace('"', '""')
    return f'"{escaped}"'


def _qualified_table(schema: str, table: str) -> str:
    return f"{_escape_identifier(schema)}.{_escape_identifier(table)}"


def _load_typed_table(
    conn: duckdb.DuckDBPyConnection,
    vocab: VocabFile,
    definition: TableDefinition,
    csv_options: CSVOptions,
    schema: str,
) -> None:
    qualified = _qualified_table(schema, definition.name)

    _create_table_if_missing(conn, definition, schema)
    conn.execute(f"DELETE FROM {qualified}")

    copy_sql = _build_copy_sql(qualified, csv_options)
    conn.execute(copy_sql, [str(vocab.path)])


def _build_copy_sql(qualified_table: str, csv_options: CSVOptions) -> str:
    options = ["FORMAT 'csv'"]
    options.append(f"DELIMITER {_sql_literal(csv_options.sep)}")
    options.append(f"HEADER {'TRUE' if csv_options.header else 'FALSE'}")
    options.append(f"QUOTE {_sql_literal(csv_options.quote)}")
    options.append(f"ESCAPE {_sql_literal(csv_options.escape)}")
    options.append(f"NULL {_sql_literal(csv_options.nullstr)}")
    if csv_options.encoding:
        options.append(f"ENCODING {_sql_literal(csv_options.encoding)}")
    options.append("DATEFORMAT '%Y%m%d'")

    return f"COPY {qualified_table} FROM ? WITH ({', '.join(options)})"


def _create_table_if_missing(
    conn: duckdb.DuckDBPyConnection,
    definition: TableDefinition,
    schema: str,
) -> None:
    qualified = _qualified_table(schema, definition.name)
    columns_sql = []
    for column in definition.columns:
        column_sql = _column_sql(column)
        columns_sql.append(column_sql)

    if definition.primary_key:
        pk = ", ".join(_escape_identifier(col) for col in definition.primary_key)
        columns_sql.append(f"PRIMARY KEY ({pk})")

    statement = (
        f"CREATE TABLE IF NOT EXISTS {qualified} (\n"
        f"    {',\n    '.join(columns_sql)}\n"
        ")"
    )

    conn.execute(statement)


def _column_sql(column: ColumnDefinition) -> str:
    parts = [
        _escape_identifier(column.name),
        column.data_type,
    ]
    if not column.nullable:
        parts.append("NOT NULL")
    return " ".join(parts)


def _load_varchar_table(
    conn: duckdb.DuckDBPyConnection,
    vocab: VocabFile,
    csv_options: CSVOptions,
    schema: str,
) -> None:
    qualified = _qualified_table(schema, vocab.table_name)
    conn.execute(f"DROP TABLE IF EXISTS {qualified}")

    sql = (
        f"CREATE TABLE {qualified} AS\n"
        f"SELECT * FROM read_csv(\n"
        f"    ?,\n"
        f"    { _csv_options_sql(csv_options) }\n"
        f");"
    )

    conn.execute(sql, [str(vocab.path)])
