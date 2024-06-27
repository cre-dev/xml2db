from typing import Union, List, Tuple

from ..exceptions import DataModelConfigError
from .column import DataModelColumn
from .relations import DataModelRelation1, DataModelRelationN
from .table import DataModelTable


class DataModelTableTransformed(DataModelTable):
    """A class extending DataModelTable with transformations

    This class allows simplifying a DataModelTable object with default or configured transformations in \
    order to reduce final schema complexity.
    """

    def _can_choice_transform_table(self) -> bool:
        """Check if the table is of type "choice" and can be transformed to type/value fields.

        Returns:
            True if the table model be converted to type/value choice model, False otherwise
        """
        if self.model_group == "choice":
            col_types = list(set([col.data_type for col in self.columns.values()]))
            return (
                len(self.relations_1) == 0
                and len(self.relations_n) == 0
                and len(col_types) == 1
            )
        return False

    def _is_table_choice_transform_applicable(self) -> bool:
        """Determine if choice transform should be applied to the whole table.

        We try the choice_transform value provided in config, if any, and otherwise fall back to default value.

        Returns:
            True if choice transform is to be applied, False otherwise.
        """
        if "choice_transform" in self.config:
            if isinstance(self.config["choice_transform"], bool):
                if self.config["choice_transform"]:
                    if self._can_choice_transform_table():
                        return True
                    else:
                        raise DataModelConfigError(
                            f"Choice-transform cannot be applied to table '{self.name}', see conditions in "
                            f"DataModelTableTransformed._can_choice_transform_table."
                        )
                else:
                    return False
            else:
                raise DataModelConfigError(
                    f"Unrecognized choice_transform value '{self.config['choice_transform']}'"
                    f" for table '{self.name}'. Only boolean values True or False are allowed."
                )
        elif self._can_choice_transform_table() and len(self.columns) > 2:
            # column number isn't reduced if the number of columns = 2, as it would be elevated to 2 columns then
            return True
        return False

    def _transform_to_choice(self) -> None:
        """Transform the current table to a choice model representation with only type and value fields"""
        col_types = list(set([col.data_type for col in self.columns.values()]))
        col_names = [col.name for col in self.columns.values()]
        min_lengths = [col.min_length for col in self.columns.values()]
        max_lengths = [col.max_length for col in self.columns.values()]
        allow_empty = [col.allow_empty for col in self.columns.values()]
        self.columns = {
            "type": DataModelColumn(
                "type",
                [("type", None)],
                "string",
                [1, 1],
                min(len(name) for name in col_names),
                max(len(name) for name in col_names),
                False,
                False,
                False,
                None,
                self.config,
                self.data_model,
            ),
            "value": DataModelColumn(
                "value",
                [("value", None)],
                col_types[0],
                [1, 1],
                min(min_lengths) if all(e is not None for e in min_lengths) else None,
                max(max_lengths) if all(e is not None for e in max_lengths) else None,
                False,
                False,
                any(allow_empty),
                None,
                self.config,
                self.data_model,
            ),
        }
        self.fields = [
            ("col", "type", self.columns["type"]),
            ("col", "value", self.columns["value"]),
        ]

    def _can_transform_field(
        self, field_type: str, field_name: str, transform: str = "join"
    ) -> bool:
        """Check if a given transformation can be applied to a given field

        Args:
            field_type: the field type ("col", "rel1" or "reln")
            field_name: the field name
            transform: the transform to be tested

        Returns:
            True is the field can be transformed
        """
        if field_type == "col" and transform == "join":
            # check if simple columns with max occurrences > 1 can be joined as string
            if self.columns[field_name].can_join_values_as_string:
                return True
        elif field_type == "rel1":
            return transform in ["elevate", "elevate_wo_prefix"]
        # "reln" can never be transformed
        return False

    def _get_field_transform(
        self, field_type: str, field_name: str
    ) -> Union[str, None]:
        """Get the transformation that should be applied to this field, taking into account user-provided config

        Args:
            field_type: the field type ("col", "rel1", "reln")
            field_name: the field name

        Returns:
            The default transformation that should be applied
        """
        field_config = self.config.get("fields", {}).get(field_name, {})
        if "transform" in field_config:
            if field_config["transform"] is False:
                return None
            if self._can_transform_field(
                field_type, field_name, field_config["transform"]
            ):
                return field_config["transform"]
            else:
                raise DataModelConfigError(
                    f"Transform value '{field_config['transform']}' cannot be applied"
                    f" to field '{field_name}' of table '{self.name}'."
                )
        else:
            if field_type == "col":
                if self._can_transform_field("col", field_name, "join"):
                    return "join"
            elif field_type == "rel1":
                if (
                    self.relations_1[field_name].occurs[0] == 1
                    or len(self.relations_1[field_name].other_table.columns) <= 4
                ) and len(self.relations_1[field_name].other_table.parents_n) == 0:
                    return (
                        "elevate_wo_prefix"
                        if len(self.columns) == 0 and len(self.relations_1) == 1
                        else "elevate"
                    )

    def _elevate_relation_1(
        self, rel_name, transform
    ) -> List[
        Tuple[str, str, Union[DataModelColumn, DataModelRelation1, DataModelRelationN]]
    ]:
        """Elevate a child table to the upper level"""
        rel = self.relations_1[rel_name]
        if transform == "elevate_wo_prefix":
            prefix = ""
        else:
            prefix = f"{rel.name}_"

        del self.relations_1[rel_name]

        # insert the children fields into the current table
        elevated_fields = []
        for child_field_type, key, child_field in rel.other_table.fields:
            prefixed_key = f"{prefix}{key}"
            if child_field_type == "col":
                self.columns[prefixed_key] = DataModelColumn(
                    prefixed_key,
                    [(rel.name, rel.other_table.type_name)] + child_field.name_chain,
                    child_field.data_type,
                    (
                        [0, child_field.occurs[1]]
                        if rel.occurs[0] == 0
                        else child_field.occurs
                    ),
                    child_field.min_length,
                    child_field.max_length,
                    child_field.is_attr,
                    child_field.is_content,
                    child_field.allow_empty,
                    child_field.ngroup,
                    self.config,
                    self.data_model,
                )
                elevated_fields.append(
                    (
                        "col",
                        prefixed_key,
                        self.columns[prefixed_key],
                    )
                )
            elif child_field_type == "rel1":
                self.relations_1[prefixed_key] = DataModelRelation1(
                    prefixed_key,
                    [(rel.name, rel.other_table.type_name)] + child_field.name_chain,
                    self,
                    child_field.other_table,
                    (
                        [0, child_field.occurs[1]]
                        if rel.occurs[0] == 0
                        else child_field.occurs
                    ),
                    child_field.ngroup,
                    self.data_model,
                )
                elevated_fields.append(
                    (
                        "rel1",
                        prefixed_key,
                        self.relations_1[prefixed_key],
                    )
                )
            elif child_field_type == "reln":
                self.relations_n[prefixed_key] = DataModelRelationN(
                    prefixed_key,
                    [(rel.name, rel.other_table.type_name)] + child_field.name_chain,
                    self,
                    child_field.other_table,
                    (
                        [0, child_field.occurs[1]]
                        if rel.occurs[0] == 0
                        else child_field.occurs
                    ),
                    child_field.ngroup,
                    self.data_model,
                )
                elevated_fields.append(
                    (
                        "reln",
                        prefixed_key,
                        self.relations_n[prefixed_key],
                    )
                )
        return elevated_fields

    def simplify_table(self) -> Tuple[dict, dict]:
        """Simplify table recursively and return a dict of simplifications applied

        Return values are dict which associate xml types and xml field with transform operations. These dicts are used
        at parsing stage and should contain all xml types and field names, even if there is no transformation to apply.
        Transformations are described by keywords:
           For tables (aka XML complex types):
              - "choice_transform": transform a choice between 2+ different fields to type / value fields in order to
              reduce the number of columns.
           For fields:
              - "join": applies to fields with multiple values allowed: append all values in a comma separated string
              - "elevate": pull up child type to parent level, appending field name to child field names
              - "elevate_wo_prefix": same as "elevate" but keeping only child's fields names (without prefixing)
              - False: prevents any transformation on this field

        Returns:
            a tuple of 2 dicts: the first one for type transforms, the second one for fields transforms
        """

        # if the table is already simplified, stop here
        if self.is_simplified:
            return {}, {}
        self.is_simplified = True

        # if the table can be transformed, stop here
        if self._is_table_choice_transform_applicable():
            self._transform_to_choice()
            self.is_simplified = True
            return {self.type_name: "choice"}, {}

        # loop through field to transform them if need be
        out_fields = []
        types_transforms = {}
        fields_transforms = {}
        for field_type, field_name, field in self.fields:
            if field_type == "col":
                if self._get_field_transform("col", field_name) == "join":
                    fields_transforms[(self.type_name, field_name)] = (
                        None,
                        "join",
                    )
                out_fields.append(("col", field_name, field))

            else:
                # simplify child table
                (
                    types_transforms_child,
                    fields_transforms_child,
                ) = field.other_table.simplify_table()
                types_transforms.update(types_transforms_child)
                fields_transforms.update(fields_transforms_child)

                # check if children can be "elevated" to the upper level
                transform = self._get_field_transform(field_type, field_name)
                if transform is not None:
                    if field_type == "rel1":
                        elevated_fields = self._elevate_relation_1(
                            field_name, transform
                        )
                        out_fields.extend(elevated_fields)
                        fields_transforms[(self.type_name, field_name)] = (
                            field.other_table.type_name,
                            transform,
                        )
                else:
                    out_fields.append((field_type, field_name, field))
                    fields_transforms[(self.type_name, field_name)] = (
                        field.other_table.type_name,
                        None,
                    )
                    field.other_table.keep_table = True

        self.fields = out_fields
        return types_transforms, fields_transforms
