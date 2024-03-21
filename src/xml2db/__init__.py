from xml2db.model import DataModel
from xml2db.document import Document
from xml2db.table import (
    DataModelTable,
    DataModelTableReused,
    DataModelTableDuplicated,
    DataModelColumn,
    DataModelRelationN,
    DataModelRelation1,
)

__all__ = [
    "DataModel",
    "Document",
    "DataModelTable",
    "DataModelTableReused",
    "DataModelTableDuplicated",
    "DataModelColumn",
    "DataModelRelation1",
    "DataModelRelationN",
]
