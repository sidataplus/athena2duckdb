from pathlib import Path
import datetime as dt

import duckdb

from athena2duckdb.loader import (
    CSVOptions,
    _create_table_if_missing,
    load_vocab_dir,
    verify_row_counts,
)
from athena2duckdb.schema import TABLE_DEFINITIONS


def test_load_and_verify_row_counts(tmp_path: Path) -> None:
    data_dir = tmp_path / "athena"
    data_dir.mkdir()

    concept = data_dir / "CONCEPT.csv"
    concept.write_text(
        "concept_id\tconcept_name\tdomain_id\tvocabulary_id\tconcept_class_id\t"
        "standard_concept\tconcept_code\tvalid_start_date\tvalid_end_date\tinvalid_reason\n"
        "1\tAlpha \"Beta\"\tCondition\tSNOMED\tClinical Finding\tS\t123\t20000101\t20991231\t\n"
        "2\tGamma's\tCondition\tSNOMED\tClinical Finding\tS\t456\t20000101\t20991231\tN\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "vocab.duckdb"

    calls: list[tuple[int, str, int]] = []
    summary = load_vocab_dir(
        data_dir,
        db_path,
        csv_options=CSVOptions(),
        progress_callback=lambda current, vocab, total: calls.append(
            (current, vocab.table_name, total)
        ),
    )

    assert db_path.exists()
    assert len(summary.vocab_files) == 1
    assert summary.vocab_files[0].table_name == "concept"
    assert summary.schema == "main"
    assert calls == [(1, "concept", 1)]

    results = verify_row_counts(db_path, summary.vocab_files, schema=summary.schema)
    assert all(result.matches for result in results)

    # Ensure the table is accessible and values were preserved literally.
    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        rows = conn.execute("SELECT concept_name FROM main.concept ORDER BY concept_id").fetchall()
        info = conn.execute("PRAGMA table_info('main.concept')").fetchall()
    finally:
        conn.close()

    assert rows == [("Alpha \"Beta\"",), ("Gamma's",)]
    type_mapping = {row[1]: row[2] for row in info}
    assert type_mapping["concept_id"].upper() == "INTEGER"
    assert type_mapping["concept_name"].upper().startswith("VARCHAR")
    assert type_mapping["valid_start_date"].upper() == "DATE"
    assert type_mapping["valid_end_date"].upper() == "DATE"

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        date_rows = conn.execute(
            "SELECT valid_start_date, valid_end_date FROM main.concept ORDER BY concept_id"
        ).fetchall()
    finally:
        conn.close()
    assert date_rows == [
        (dt.date(2000, 1, 1), dt.date(2099, 12, 31)),
        (dt.date(2000, 1, 1), dt.date(2099, 12, 31)),
    ]


def test_create_table_if_missing_is_idempotent_for_typed_table() -> None:
    conn = duckdb.connect(":memory:")
    try:
        definition = TABLE_DEFINITIONS["concept"]
        _create_table_if_missing(conn, definition, "main")
        _create_table_if_missing(conn, definition, "main")
        info = conn.execute("PRAGMA table_info('main.concept')").fetchall()
    finally:
        conn.close()

    primary_key_columns = [row[1] for row in info if row[5] > 0]
    assert primary_key_columns == ["concept_id"]


def test_schema_includes_all_vocab_tables_and_overflow_safe_numerator() -> None:
    expected_vocab_tables = {
        "concept",
        "vocabulary",
        "domain",
        "concept_class",
        "concept_relationship",
        "relationship",
        "concept_synonym",
        "concept_ancestor",
        "source_to_concept_map",
        "drug_strength",
    }

    assert expected_vocab_tables.issubset(set(TABLE_DEFINITIONS))

    drug_strength = TABLE_DEFINITIONS["drug_strength"]
    col_types = {column.name: column.data_type.upper() for column in drug_strength.columns}
    assert col_types["numerator_value"] == "DECIMAL(38,16)"


def test_load_source_to_concept_map_and_drug_strength_typed_values(tmp_path: Path) -> None:
    data_dir = tmp_path / "athena"
    data_dir.mkdir()

    source_to_concept_map = data_dir / "SOURCE_TO_CONCEPT_MAP.csv"
    source_to_concept_map.write_text(
        "source_code\tsource_concept_id\tsource_vocabulary_id\tsource_code_description\t"
        "target_concept_id\ttarget_vocabulary_id\tvalid_start_date\tvalid_end_date\tinvalid_reason\n"
        "ABC123\t0\tTESTVOC\tTest description\t12345\tSNOMED\t20210131\t20991231\t\n",
        encoding="utf-8",
    )

    drug_strength = data_dir / "DRUG_STRENGTH.csv"
    drug_strength.write_text(
        "drug_concept_id\tingredient_concept_id\tamount_value\tamount_unit_concept_id\t"
        "numerator_value\tnumerator_unit_concept_id\tdenominator_value\t"
        "denominator_unit_concept_id\tbox_size\tvalid_start_date\tvalid_end_date\tinvalid_reason\n"
        "1\t2\t\t\t2340000000000000\t8576\t\t\t\t20210630\t20991231\t\n",
        encoding="utf-8",
    )

    db_path = tmp_path / "vocab.duckdb"
    summary = load_vocab_dir(data_dir, db_path, csv_options=CSVOptions())
    assert {v.table_name for v in summary.vocab_files} == {
        "source_to_concept_map",
        "drug_strength",
    }

    conn = duckdb.connect(str(db_path), read_only=True)
    try:
        source_dates = conn.execute(
            "SELECT valid_start_date, valid_end_date "
            "FROM main.source_to_concept_map"
        ).fetchall()
        numerator_rows = conn.execute(
            "SELECT CAST(numerator_value AS VARCHAR), typeof(numerator_value) "
            "FROM main.drug_strength"
        ).fetchall()
    finally:
        conn.close()

    assert source_dates == [(dt.date(2021, 1, 31), dt.date(2099, 12, 31))]
    assert numerator_rows == [("2340000000000000.0000000000000000", "DECIMAL(38,16)")]
