import logging
from typing import List, Iterable, Any, Union, TYPE_CHECKING

from sqlalchemy import Column

if TYPE_CHECKING:
    from ..model import DataModel

logger = logging.getLogger(__name__)


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
        has_suffix: bool,
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
        self.has_suffix = has_suffix
        self.is_content = is_content
        self.allow_empty = allow_empty
        self.ngroup = ngroup
        self.model_config = model_config
        self.data_model = data_model
        self.other_table = None  # just to avoid a linting warning

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
                "base64Binary",  # was added as a fix for accepting more schemas, but not ideal
                "decimal",  # was added as a fix for accepting more schemas, but not ideal
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
        ) or self.data_model.dialect.column_type(self, temp)
        db_col = self.data_model.dialect.db_identifier(self.name)
        yield Column(db_col, column_type, key=self.name)
