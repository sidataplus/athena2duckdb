## OMOP Athena → DuckDB

`athena2duckdb` converts an extracted OMOP vocabulary download from
[OHDSI Athena](https://athena.ohdsi.org/) into a ready-to-query DuckDB file with
typed CDM tables, primary keys, and automatic row-count validation. The loader
ingests the standard OMOP vocab files (`CONCEPT.csv`, `VOCABULARY.csv`, etc.)
and skips auxiliary exports like `CONCEPT_CPT4.csv` or `README.txt` by default.

### Features
- Discovers standard OMOP vocabulary files such as `CONCEPT.csv`,
  `VOCABULARY.csv`, `CONCEPT_RELATIONSHIP.csv`, and more.
- Streams each file into DuckDB using `read_csv` with quoting/escaping disabled,
  preventing parse failures caused by embedded quotes or backslashes, while the
  CLI shows a live progress bar per table.
- Loads recognised vocab files into typed tables (INTEGER, DATE, VARCHAR) that
  match the CDM DDL with primary keys already enforced (secondary indexes can be
  added later if needed).
- Always performs row-count verification to ensure the database matches source
  files.

### Installation

From PyPI:

```bash
pip install athena2duckdb
```

For local development:

```bash
uv sync
```

or build/install directly from the project root:

```bash
uv build
pip install dist/athena2duckdb-*.whl
```

### CLI Usage

```bash
uv run athena2duckdb /path/to/athena-export --verbose
```

Arguments:

| Flag | Description |
|------|-------------|
| `input_dir` | Directory that contains the Athena CSV/TSV files. |
| `-o, --out` | Output DuckDB database file (default `omop_vocab.duckdb`). |
| `--sep` | Field delimiter (default tab). |
| `--encoding` | Source file encoding (default `UTF-8`). |
| `--threads` | Number of DuckDB threads to use. |
| `--schema` | DuckDB schema name for created tables (default `main`). |
| `--overwrite` | Replace an existing DuckDB file if present. |
| `--verbose` | Emit INFO-level logs during the load. |

### Example

```bash
uv run athena2duckdb data/
```

Sample output:

```
Loaded 10 tables into omop_vocab.duckdb.
Tables: concept, concept_ancestor, concept_class, concept_relationship, concept_synonym,
domain, drug_strength, source_to_concept_map, relationship, vocabulary
OK        table=concept                  csv_rows=93,547 table_rows=93,547
...
```

### Programmatic API

```python
from pathlib import Path
from athena2duckdb import CSVOptions, load_vocab_dir, verify_row_counts

summary = load_vocab_dir(Path("data"), Path("omop_vocab.duckdb"), schema="cdm")
results = verify_row_counts(summary.db_path, summary.vocab_files, schema=summary.schema)
```

### Testing

```bash
uv run pytest
```

### Releasing

See [RELEASING.md](RELEASING.md).

### License

This project is licensed under the MIT License. See [LICENSE](LICENSE).
