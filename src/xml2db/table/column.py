import logging
from typing import List, Iterable, Any, Union, TYPE_CHECKING

from sqlalchemy import (
    Integer,
    Double,
    Boolean,
    BigInteger,
    SmallInteger,
    Column,
    DateTime,
    String,
    LargeBinary,
)
from sqlalchemy.dialects import mssql, mysql

if TYPE_CHECKING:
    from ..model import DataModel

logger = logging.getLogger(__name__)


def types_mapping_default(temp: bool, col: "DataModelColumn") -> Any:
    """Defines the sqlalchemy type to use for given column properties in target tables

    Args:
        temp: are we targeting the temporary tables schema or the final tables?
        col: an object representing a column of a table for which we are determining the SQL type to define

    Returns:
        a sqlalchemy class representing the data type to be used
    """
    if col.occurs[1] != 1:
        return String(8000)
    if col.data_type in ["decimal", "float"]:
        return Double
    if col.data_type == "dateTime":
        return DateTime(timezone=True)
    if col.data_type == "integer" or col.data_type == "int":
        return Integer
    if col.data_type == "boolean":
        return Boolean
    if col.data_type == "byte":
        return SmallInteger
    if col.data_type == "long":
        return BigInteger
    if col.data_type == "date":
        return String(16)
    if col.data_type == "time":
        return String(18)
    if col.data_type in ["string", "NMTOKEN", "duration", "token"]:
        if col.max_length is None:
            return String(1000)
        min_length = 0 if col.min_length is None else col.min_length
        if min_length >= col.max_length - 1 and not col.allow_empty:
            return String(col.max_length)
        return String(col.max_length)
    if col.data_type == "binary":
        return LargeBinary(col.max_length)
    else:
        logger.warning(
            f"unknown type '{col.data_type}' for column '{col.name}', defaulting to VARCHAR(1000) "
            f"(this can be overridden by providing a field type in the configuration)"
        )
        return String(1000)


def types_mapping_mssql(temp: bool, col: "DataModelColumn") -> Any:
    """Defines the MSSQL type to use for given column properties in target tables

    Args:
        temp: are we targeting the temporary tables schema or the final tables?
        col: an object representing a column of a table for which we are determining the SQL type to define

    Returns:
        a sqlalchemy class representing the data type to be used
    """
    if col.occurs[1] != 1:
        return mssql.VARCHAR(8000)
    if col.data_type in ["decimal", "float"]:
        return Double
    if col.data_type == "dateTime":
        # using the DATETIMEOFFSET directly in the temporary table caused issues when inserting data in the target
        # table with INSERT INTO SELECT converts datetime VARCHAR to DATETIMEOFFSET without errors
        return mssql.VARCHAR(100) if temp else mssql.DATETIMEOFFSET
    if col.data_type == "integer" or col.data_type == "int":
        return Integer
    if col.data_type == "boolean":
        return Boolean
    if col.data_type == "byte":
        return SmallInteger
    if col.data_type == "long":
        return BigInteger
    if col.data_type == "date":
        return mssql.VARCHAR(16)
    if col.data_type == "time":
        return mssql.VARCHAR(18)
    if col.data_type in ["string", "NMTOKEN", "duration", "token"]:
        if col.max_length is None:
            return mssql.VARCHAR(1000)
        min_length = 0 if col.min_length is None else col.min_length
        if min_length >= col.max_length - 1 and not col.allow_empty:
            return mssql.CHAR(col.max_length)
        return mssql.VARCHAR(col.max_length)
    if col.data_type == "binary":
        if col.max_length == col.min_length:
            return mssql.BINARY(col.max_length)
        return mssql.VARBINARY(col.max_length)
    else:
        logger.warning(
            f"unknown type '{col.data_type}' for column '{col.name}', defaulting to VARCHAR(1000) "
            f"(this can be overridden by providing a field type in the configuration)"
        )
        return mssql.VARCHAR(1000)


def types_mapping_mysql(temp: bool, col: "DataModelColumn") -> Any:
    """Defines the MySQL/sqlalchemy type to use for given column properties in target tables

    Args:
        temp: are we targeting the temporary tables schema or the final tables?
        col: an object representing a column of a table for which we are determining the SQL type to define

    Returns:
        a sqlalchemy class representing the data type to be used
    """
    if col.occurs[1] != 1:
        return String(4000)
    if col.data_type in ["string", "NMTOKEN", "duration", "token"]:
        if col.max_length is None:
            return String(255)
    if col.data_type == "binary":
        if col.max_length == col.min_length:
            return mysql.BINARY(col.max_length)
        return mysql.VARBINARY(col.max_length)
    return types_mapping_default(temp, col)


class DataModelColumn:
    """A class representing a column of a table

    Args:
        name: column name
        data_type: column data type
        occurs: min and max occurrences of the field
        min_length: min length
        max_length: max length
        is_attr: does the column value come from an xml attribute?
        is_content: is the column used to store the content value of a mixed complex type?
        allow_empty: is nullable ?
        ngroup: a key used to handle nested sequences
        model_config: data model config, may contain column type information
        data_model: the DataModel object it belongs to

    Attributes:
        name: the name of the field (i.e. column name)
        data_type: the data type, extracted from XSD data type
        occurs: list of int with two elements: min occurrences and max occurrences. Max occurrences is None if unbounded
    """

    def __init__(
        self,
        name: str,
        name_chain: list,
        data_type: str,
        occurs: List[int],
        min_length: int,
        max_length: Union[int, None],
        is_attr: bool,
        is_content: bool,
        allow_empty: bool,
        ngroup: Union[int, None],
        model_config: dict[str, Any],
        data_model: "DataModel",
    ):
        """Constructor method"""
        self.name = name
        self.name_chain = name_chain
        self.data_type = data_type
        self.occurs = occurs
        self.min_length = min_length
        self.max_length = max_length
        self.is_attr = is_attr
        self.is_content = is_content
        self.allow_empty = allow_empty
        self.ngroup = ngroup
        self.model_config = model_config
        self.data_model = data_model
        self.other_table = None  # just to avoid a linting warning
        self.types_mapping = (
            types_mapping_mssql
            if data_model.db_type == "mssql"
            else (
                types_mapping_mysql
                if data_model.db_type == "mysql"
                else types_mapping_default
            )
        )

    @property
    def can_join_values_as_string(self):
        """Decide whether multiple values can be stored as comma separated values in this column

        Returns:
            True if data type is compatible with comma separated values

        Raises:
            ValueError: if data type does not allow storage as comma separated values
        """
        if self.occurs[1] == 1:
            return True
        if self.occurs[1] is None or self.occurs[1] > 1:
            if self.data_type in (
                "string",
                "date",
                "dateTime",
                "NMTOKEN",
                "time",
            ):
                return True
            raise ValueError(
                f"Col type '{self.data_type}' with maxOccur > 1 is not supported."
            )
        return False

    def get_sqlalchemy_column(self, temp: bool = False) -> Iterable[Column]:
        """Create sqlalchemy Column object

        Args:
            temp: temp table or target table ?
        """
        # use type specified in config if exists
        column_type = self.model_config.get("fields", {}).get(self.name, {}).get(
            "type"
        ) or self.types_mapping(temp, self)

        yield Column(self.name, column_type)
