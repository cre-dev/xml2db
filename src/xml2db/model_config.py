import hashlib
import logging
from typing import Callable, Iterable, Union, Any

from sqlalchemy.types import TypeEngine

try:
    from typing import TypedDict, NotRequired
except ImportError:
    from typing_extensions import TypedDict, NotRequired


logger = logging.getLogger(__name__)


class DataModelConfigError(Exception):
    """An exception to raise when model config provided by the user is erroneous"""

    pass


def runtime_type_check(src: dict, key: str, exp_type: Any, default: Any):
    """Check type of dict member, with default value

    Args:
        src: a dict containing member to check
        key: the dict key of the member to check
        exp_type: expected type for the member
        default: default value

    Returns:
        The dict member value
    """
    if exp_type.__name__ == "callable":
        if key in src and not callable(src[key]):
            raise DataModelConfigError(f"'{key}' must be callable")
    else:
        if key in src and not isinstance(src[key], exp_type):
            raise DataModelConfigError(f"'{key}' must be a {exp_type.__name__}")
    return src.get(key, default)


class FieldConfigType(TypedDict):
    type: NotRequired[TypeEngine]
    transform: NotRequired[Union[str, bool]]


class TableConfigType(TypedDict):
    fields: NotRequired[dict[str, FieldConfigType]]
    choice_transform: NotRequired[bool]
    reuse: NotRequired[bool]
    extra_args: NotRequired[Union[Iterable, Callable[[], Iterable]]]


class DataModelConfigType(TypedDict):
    tables: NotRequired[dict[str, TableConfigType]]
    as_columnstore: NotRequired[bool]
    row_numbers: NotRequired[bool]
    document_tree_hook: NotRequired[Callable[[tuple], tuple]]
    document_tree_node_hook: NotRequired[Callable[[tuple], tuple]]
    record_hash_column_name: NotRequired[str]
    record_hash_constructor: NotRequired[Callable]
    record_hash_size: NotRequired[int]
    metadata_columns: NotRequired[list[dict[str, Any]]]


def validate_table_config(cfg: TableConfigType, db_type: str) -> TableConfigType:
    """Validate a table dict config

    Args:
        cfg: a dict config to validate
        db_type: database type

    Returns:
        The validated config dict
    """
    if cfg is None:
        cfg = {}

    config = {
        "reuse": runtime_type_check(cfg, "reuse", bool, True),
        "as_columnstore": runtime_type_check(cfg, "as_columnstore", bool, False),
    }
    if "extra_args" in cfg and not (
        isinstance(cfg["extra_args"], list)
        or isinstance(cfg["extra_args"], tuple)
        or callable(cfg["extra_args"])
    ):
        raise DataModelConfigError("extra_args must be a list, a tuple or callable")
    config["extra_args"] = cfg.get("extra_args", [])
    if "choice_transform" in cfg:
        config["choice_transform"] = runtime_type_check(
            cfg, "choice_transform", bool, False
        )

    if config["as_columnstore"] and not db_type == "mssql":
        config["as_columnstore"] = False
        logger.warning(
            "Clustered columnstore indexes are only supported with MS SQL Server database"
        )

    config["fields"] = cfg.get("fields", {})

    return config


def validate_model_config(
    cfg: DataModelConfigType, db_type: str
) -> DataModelConfigType:
    """Validate the model config dict

    Args:
        cfg: a dict config to validate
        db_type: database type

    Returns:
        The validated config dict

    """
    if cfg is None:
        cfg = {}
    model_config = {
        key: runtime_type_check(cfg, key, exp_type, default)
        for key, exp_type, default in [
            ("as_columnstore", bool, False),
            ("row_numbers", bool, False),
            ("document_tree_hook", callable, None),
            ("document_tree_node_hook", callable, None),
            ("record_hash_column_name", str, "xml2db_record_hash"),
            ("record_hash_constructor", callable, hashlib.sha1),
            ("record_hash_size", int, 20),
            ("metadata_columns", list, []),
        ]
    }
    if model_config["as_columnstore"] and db_type != "mssql":
        model_config["as_columnstore"] = False
        logger.info(
            "Clustered columnstore indexes are only supported with MS SQL Server database, noop"
        )

    model_config["tables"] = {
        table_name: validate_table_config(table_cfg, db_type)
        for table_name, table_cfg in cfg.get("tables", {}).items()
    }

    return model_config
