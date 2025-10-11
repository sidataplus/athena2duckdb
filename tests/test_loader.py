from pathlib import Path

import duckdb

from athena2duckdb.loader import CSVOptions, load_vocab_dir, verify_row_counts


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
