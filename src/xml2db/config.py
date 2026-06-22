"""Typed config definitions and YAML loading utilities for xml2db."""
from __future__ import annotations

import re
from typing import Any, TypedDict

import sqlalchemy as sa

from .exceptions import DataModelConfigError

# Keys that require Python callables — cannot be expressed in YAML
_CALLABLE_ONLY_KEYS: frozenset[str] = frozenset(
    {"document_tree_hook", "document_tree_node_hook", "record_hash_constructor"}
)

# ---------------------------------------------------------------------------
# SQLAlchemy type resolver
# ---------------------------------------------------------------------------

_SA_TYPE_MAP: dict[str, type] = {
    "String": sa.String,
    "Text": sa.Text,
    "Integer": sa.Integer,
    "BigInteger": sa.BigInteger,
    "SmallInteger": sa.SmallInteger,
    "Float": sa.Float,
    "Double": sa.Double,
    "Numeric": sa.Numeric,
    "Boolean": sa.Boolean,
    "DateTime": sa.DateTime,
    "Date": sa.Date,
    "Time": sa.Time,
    "LargeBinary": sa.LargeBinary,
    "JSON": sa.JSON,
    "Uuid": sa.Uuid,
    "UUID": sa.Uuid,
}

_TYPE_RE = re.compile(r"^(\w+)(?:\(([^)]*)\))?$")


def _parse_type_arg(s: str) -> Any:
    s = s.strip()
    if s in ("True", "true"):
        return True
    if s in ("False", "false"):
        return False
    try:
        return int(s)
    except ValueError:
        pass
    try:
        return float(s)
    except ValueError:
        pass
    if len(s) >= 2 and s[0] in ('"', "'") and s[-1] == s[0]:
        return s[1:-1]
    raise DataModelConfigError(f"Cannot parse type argument value: '{s}'")


def resolve_sa_type(type_spec: Any) -> Any:
    """Resolve a SQLAlchemy type name string to a type instance, or pass through.

    Args:
        type_spec: A string such as ``"String(100)"``, ``"Integer"``,
            ``"DateTime(timezone=True)"``, or an existing SQLAlchemy type
            instance / class (returned unchanged).

    Returns:
        A SQLAlchemy type instance.

    Raises:
        DataModelConfigError: If the string cannot be parsed or names an
            unknown type.
    """
    if not isinstance(type_spec, str):
        return type_spec  # already a SQLAlchemy type — pass through

    m = _TYPE_RE.match(type_spec.strip())
    if not m:
        raise DataModelConfigError(f"Cannot parse SQLAlchemy type: '{type_spec}'")

    type_name, args_str = m.group(1), m.group(2)
    if type_name not in _SA_TYPE_MAP:
        raise DataModelConfigError(
            f"Unknown SQLAlchemy type '{type_name}'. "
            f"Supported: {', '.join(sorted(_SA_TYPE_MAP))}"
        )

    type_cls = _SA_TYPE_MAP[type_name]
    if not args_str or not args_str.strip():
        return type_cls()

    args: list = []
    kwargs: dict = {}
    for part in args_str.split(","):
        part = part.strip()
        if not part:
            continue
        if "=" in part:
            k, _, v = part.partition("=")
            kwargs[k.strip()] = _parse_type_arg(v)
        else:
            args.append(_parse_type_arg(part))

    return type_cls(*args, **kwargs)


# ---------------------------------------------------------------------------
# TypedDicts
# ---------------------------------------------------------------------------

class FieldConfig(TypedDict, total=False):
    type: Any  # str (e.g. "String(100)") or SQLAlchemy type — Python only when not a str
    rename: str
    transform: Any  # str | False


class IndexConfig(TypedDict, total=False):
    name: str         # Index name (required)
    columns: list[str]  # Column names (required)
    unique: bool


class TableConfig(TypedDict, total=False):
    reuse: bool
    as_columnstore: bool
    choice_transform: bool
    # In YAML: list of IndexConfig dicts.  In Python: list/tuple of SQLAlchemy
    # schema objects, or a zero-argument callable returning such a list.
    extra_args: list[IndexConfig] | list[Any] | Any
    fields: dict[str, FieldConfig]


class MetadataColumnConfig(TypedDict, total=False):
    name: str   # Required — column name
    type: Any   # Required — str (e.g. "String(100)") or SQLAlchemy type
    nullable: bool
    default: Any
    server_default: Any
    comment: str
    index: bool
    unique: bool


class ModelConfig(TypedDict, total=False):
    as_columnstore: bool
    row_numbers: bool
    document_tree_hook: Any        # callable — Python only
    document_tree_node_hook: Any   # callable — Python only
    record_hash_column_name: str
    record_hash_constructor: Any   # callable — Python only
    record_hash_size: int
    metadata_columns: list[MetadataColumnConfig]
    tables: dict[str, TableConfig]


# ---------------------------------------------------------------------------
# YAML parsing + validation
# ---------------------------------------------------------------------------

def _check_config(data: dict, *, from_yaml: bool) -> None:
    """Validate a raw config dict, raising DataModelConfigError on Python-only values."""
    if not from_yaml:
        return  # dict configs are trusted; no checks needed

    # Model-level callable-only keys
    for key in _CALLABLE_ONLY_KEYS:
        if key in data:
            raise DataModelConfigError(
                f"'{key}' requires a Python callable and cannot be set in a YAML config "
                "file. Pass a Python dict with the callable directly instead."
            )

    # metadata_columns — each entry's 'type' must be a string
    for i, col_cfg in enumerate(data.get("metadata_columns", [])):
        if not isinstance(col_cfg, dict):
            raise DataModelConfigError(
                f"metadata_columns[{i}] must be a mapping with at least 'name' and 'type'."
            )
        if "type" in col_cfg and not isinstance(col_cfg["type"], str):
            raise DataModelConfigError(
                f"metadata_columns[{i}].type must be a string (e.g. 'String(100)') "
                "in a YAML config file."
            )

    # Table- and field-level checks
    for table_name, table_cfg in data.get("tables", {}).items():
        if not isinstance(table_cfg, dict):
            continue
        # extra_args must be a list (callable not possible from YAML)
        if "extra_args" in table_cfg and callable(table_cfg["extra_args"]):
            raise DataModelConfigError(
                f"tables.{table_name}.extra_args is a callable and cannot be set in a "
                "YAML config file. Pass a Python dict with the callable directly instead."
            )
        for field_name, field_cfg in table_cfg.get("fields", {}).items():
            if not isinstance(field_cfg, dict):
                continue
            if "type" in field_cfg and not isinstance(field_cfg["type"], str):
                raise DataModelConfigError(
                    f"tables.{table_name}.fields.{field_name}.type must be a string "
                    "(e.g. 'String(100)') in a YAML config file."
                )


def parse_yaml_config(text: str) -> ModelConfig:
    """Parse a YAML string into a model config dict.

    Args:
        text: YAML text representing a model config mapping.

    Returns:
        A :class:`ModelConfig` dict.

    Raises:
        DataModelConfigError: If the config contains keys that require Python
            objects (callables or SQLAlchemy types) or if the top level is not
            a mapping.
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
        raise DataModelConfigError("Config must be a YAML mapping at the top level.")

    _check_config(data, from_yaml=True)
    return data


def load_config(path: str) -> ModelConfig:
    """Load a model config from a YAML file.

    Args:
        path: Path to a YAML file containing the model config.

    Returns:
        A :class:`ModelConfig` dict.

    Raises:
        DataModelConfigError: If the file contains keys that require Python objects.
        ImportError: If PyYAML is not installed.
    """
    with open(path, encoding="utf-8") as f:
        return parse_yaml_config(f.read())
