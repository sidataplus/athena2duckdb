from pathlib import Path

from athena2duckdb.tables import KNOWN_TABLES, discover_vocab_files


def write_file(path: Path, contents: str) -> None:
    path.write_text(contents, encoding="utf-8")


def test_discover_vocab_files_known_and_unknown(tmp_path: Path) -> None:
    concept = tmp_path / "CONCEPT.csv"
    vocabulary = tmp_path / "VOCABULARY.csv"
    custom = tmp_path / "Custom-File.csv"

    write_file(concept, "concept_id\n1\n")
    write_file(vocabulary, "vocabulary_id\n1\n")
    write_file(custom, "col\nvalue\n")

    vocab_files = discover_vocab_files(tmp_path)

    mapping = {vf.table_name: vf.path.name for vf in vocab_files}

    assert mapping[KNOWN_TABLES["CONCEPT.CSV"]] == "CONCEPT.csv"
    assert mapping[KNOWN_TABLES["VOCABULARY.CSV"]] == "VOCABULARY.csv"
    assert "custom_file" not in mapping
