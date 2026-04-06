"""Canonical table definitions for typed OMOP vocabulary loading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class ColumnDefinition:
    name: str
    data_type: str
    nullable: bool


@dataclass(frozen=True)
class IndexDefinition:
    name: str
    columns: Sequence[str]


@dataclass(frozen=True)
class TableDefinition:
    name: str
    columns: Sequence[ColumnDefinition]
    primary_key: Sequence[str] | None = None
    indexes: Sequence[IndexDefinition] = ()


TABLE_DEFINITIONS: dict[str, TableDefinition] = {
    "concept": TableDefinition(
        name="concept",
        columns=(
            ColumnDefinition("concept_id", "INTEGER", False),
            ColumnDefinition("concept_name", "VARCHAR(255)", False),
            ColumnDefinition("domain_id", "VARCHAR(20)", False),
            ColumnDefinition("vocabulary_id", "VARCHAR(20)", False),
            ColumnDefinition("concept_class_id", "VARCHAR(20)", False),
            ColumnDefinition("standard_concept", "VARCHAR(1)", True),
            ColumnDefinition("concept_code", "VARCHAR(50)", False),
            ColumnDefinition("valid_start_date", "DATE", False),
            ColumnDefinition("valid_end_date", "DATE", False),
            ColumnDefinition("invalid_reason", "VARCHAR(1)", True),
        ),
        primary_key=("concept_id",),
        indexes=(
            IndexDefinition("idx_concept_concept_id", ("concept_id",)),
            IndexDefinition("idx_concept_code", ("concept_code",)),
            IndexDefinition("idx_concept_vocabluary_id", ("vocabulary_id",)),
            IndexDefinition("idx_concept_domain_id", ("domain_id",)),
            IndexDefinition("idx_concept_class_id", ("concept_class_id",)),
        ),
    ),
    "vocabulary": TableDefinition(
        name="vocabulary",
        columns=(
            ColumnDefinition("vocabulary_id", "VARCHAR(20)", False),
            ColumnDefinition("vocabulary_name", "VARCHAR(255)", False),
            ColumnDefinition("vocabulary_reference", "VARCHAR(255)", True),
            ColumnDefinition("vocabulary_version", "VARCHAR(255)", True),
            ColumnDefinition("vocabulary_concept_id", "INTEGER", False),
        ),
        primary_key=("vocabulary_id",),
        indexes=(
            IndexDefinition("idx_vocabulary_vocabulary_id", ("vocabulary_id",)),
        ),
    ),
    "domain": TableDefinition(
        name="domain",
        columns=(
            ColumnDefinition("domain_id", "VARCHAR(20)", False),
            ColumnDefinition("domain_name", "VARCHAR(255)", False),
            ColumnDefinition("domain_concept_id", "INTEGER", False),
        ),
        primary_key=("domain_id",),
        indexes=(
            IndexDefinition("idx_domain_domain_id", ("domain_id",)),
        ),
    ),
    "concept_class": TableDefinition(
        name="concept_class",
        columns=(
            ColumnDefinition("concept_class_id", "VARCHAR(20)", False),
            ColumnDefinition("concept_class_name", "VARCHAR(255)", False),
            ColumnDefinition("concept_class_concept_id", "INTEGER", False),
        ),
        primary_key=("concept_class_id",),
        indexes=(
            IndexDefinition("idx_concept_class_class_id", ("concept_class_id",)),
        ),
    ),
    "concept_relationship": TableDefinition(
        name="concept_relationship",
        columns=(
            ColumnDefinition("concept_id_1", "INTEGER", False),
            ColumnDefinition("concept_id_2", "INTEGER", False),
            ColumnDefinition("relationship_id", "VARCHAR(20)", False),
            ColumnDefinition("valid_start_date", "DATE", False),
            ColumnDefinition("valid_end_date", "DATE", False),
            ColumnDefinition("invalid_reason", "VARCHAR(1)", True),
        ),
        indexes=(
            IndexDefinition("idx_concept_relationship_id_1", ("concept_id_1",)),
            IndexDefinition("idx_concept_relationship_id_2", ("concept_id_2",)),
            IndexDefinition("idx_concept_relationship_id_3", ("relationship_id",)),
        ),
    ),
    "relationship": TableDefinition(
        name="relationship",
        columns=(
            ColumnDefinition("relationship_id", "VARCHAR(20)", False),
            ColumnDefinition("relationship_name", "VARCHAR(255)", False),
            ColumnDefinition("is_hierarchical", "VARCHAR(1)", False),
            ColumnDefinition("defines_ancestry", "VARCHAR(1)", False),
            ColumnDefinition("reverse_relationship_id", "VARCHAR(20)", False),
            ColumnDefinition("relationship_concept_id", "INTEGER", False),
        ),
        primary_key=("relationship_id",),
        indexes=(
            IndexDefinition("idx_relationship_rel_id", ("relationship_id",)),
        ),
    ),
    "concept_synonym": TableDefinition(
        name="concept_synonym",
        columns=(
            ColumnDefinition("concept_id", "INTEGER", False),
            ColumnDefinition("concept_synonym_name", "VARCHAR(1000)", False),
            ColumnDefinition("language_concept_id", "INTEGER", False),
        ),
        indexes=(
            IndexDefinition("idx_concept_synonym_id", ("concept_id",)),
        ),
    ),
    "concept_ancestor": TableDefinition(
        name="concept_ancestor",
        columns=(
            ColumnDefinition("ancestor_concept_id", "INTEGER", False),
            ColumnDefinition("descendant_concept_id", "INTEGER", False),
            ColumnDefinition("min_levels_of_separation", "INTEGER", False),
            ColumnDefinition("max_levels_of_separation", "INTEGER", False),
        ),
        indexes=(
            IndexDefinition("idx_concept_ancestor_id_1", ("ancestor_concept_id",)),
            IndexDefinition("idx_concept_ancestor_id_2", ("descendant_concept_id",)),
        ),
    ),
    "source_to_concept_map": TableDefinition(
        name="source_to_concept_map",
        columns=(
            ColumnDefinition("source_code", "VARCHAR(50)", False),
            ColumnDefinition("source_concept_id", "INTEGER", False),
            ColumnDefinition("source_vocabulary_id", "VARCHAR(20)", False),
            ColumnDefinition("source_code_description", "VARCHAR(255)", True),
            ColumnDefinition("target_concept_id", "INTEGER", False),
            ColumnDefinition("target_vocabulary_id", "VARCHAR(20)", False),
            ColumnDefinition("valid_start_date", "DATE", False),
            ColumnDefinition("valid_end_date", "DATE", False),
            ColumnDefinition("invalid_reason", "VARCHAR(1)", True),
        ),
        indexes=(
            IndexDefinition("idx_source_to_concept_map_3", ("target_concept_id",)),
            IndexDefinition("idx_source_to_concept_map_1", ("source_vocabulary_id",)),
            IndexDefinition("idx_source_to_concept_map_2", ("target_vocabulary_id",)),
            IndexDefinition("idx_source_to_concept_map_c", ("source_code",)),
        ),
    ),
    "drug_strength": TableDefinition(
        name="drug_strength",
        columns=(
            ColumnDefinition("drug_concept_id", "INTEGER", False),
            ColumnDefinition("ingredient_concept_id", "INTEGER", False),
            ColumnDefinition("amount_value", "NUMERIC", True),
            ColumnDefinition("amount_unit_concept_id", "INTEGER", True),
            ColumnDefinition("numerator_value", "DECIMAL(38,16)", True),
            ColumnDefinition("numerator_unit_concept_id", "INTEGER", True),
            ColumnDefinition("denominator_value", "NUMERIC", True),
            ColumnDefinition("denominator_unit_concept_id", "INTEGER", True),
            ColumnDefinition("box_size", "INTEGER", True),
            ColumnDefinition("valid_start_date", "DATE", False),
            ColumnDefinition("valid_end_date", "DATE", False),
            ColumnDefinition("invalid_reason", "VARCHAR(1)", True),
        ),
        indexes=(
            IndexDefinition("idx_drug_strength_id_1", ("drug_concept_id",)),
            IndexDefinition("idx_drug_strength_id_2", ("ingredient_concept_id",)),
        ),
    ),
}
