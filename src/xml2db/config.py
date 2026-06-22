"""Typed config definitions and YAML loading utilities for xml2db."""
from __future__ import annotations

from typing import Any, TypedDict

from .exceptions import DataModelConfigError

# Keys that require Python callables — cannot be expressed in YAML
_CALLABLE_ONLY_KEYS: frozenset[str] = frozenset(
    {"document_tree_hook", "document_tree_node_hook", "record_hash_constructor"}
)


class FieldConfig(TypedDict, total=False):
    type: Any  # SQLAlchemy column type — Python only, not settable via YAML
    rename: str
    transform: Any  # str | False


class TableConfig(TypedDict, total=False):
    reuse: bool
    as_columnstore: bool
    choice_transform: bool
    extra_args: Any  # list | tuple | callable — callable is Python only
    fields: dict[str, FieldConfig]


class ModelConfig(TypedDict, total=False):
    as_columnstore: bool
    row_numbers: bool
    document_tree_hook: Any  # callable — Python only
    document_tree_node_hook: Any  # callable — Python only
    record_hash_column_name: str
    record_hash_constructor: Any  # callable — Python only
    record_hash_size: int
    metadata_columns: list
    tables: dict[str, TableConfig]


def parse_yaml_config(text: str) -> ModelConfig:
    """Parse a YAML string into a model config dict.

    Args:
        text: YAML text representing a model config mapping.

    Returns:
        A ModelConfig dict.

    Raises:
        DataModelConfigError: If the YAML contains keys that require Python objects
            (callables), or if the top level is not a mapping.
        ImportError: If PyYAML is not installed.
    """
    try:
        import yaml
    except ImportError:
        raise ImportError(
            "PyYAML is required to parse YAML config. Install with: pip install pyyaml"
        )

    data = yaml.safe_load(text)
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise DataModelConfigError(
            "Config must be a YAML mapping at the top level."
        )
    for key in _CALLABLE_ONLY_KEYS:
        if key in data:
            raise DataModelConfigError(
                f"'{key}' requires a Python callable and cannot be set in a YAML config "
                "file. Pass a Python dict with the callable directly instead."
            )
    return data


def load_config(path: str) -> ModelConfig:
    """Load a model config from a YAML file.

    Args:
        path: Path to a YAML file containing the model config.

    Returns:
        A ModelConfig dict.

    Raises:
        DataModelConfigError: If the file contains keys that require Python objects.
        ImportError: If PyYAML is not installed.
    """
    with open(path, encoding="utf-8") as f:
        return parse_yaml_config(f.read())
