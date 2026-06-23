"""Tests for config.py (resolve_sa_type, parse_yaml_config) and model-level
transform option."""
import os
import textwrap

import pytest
import sqlalchemy as sa

from xml2db import DataModel
from xml2db.config import parse_yaml_config, resolve_sa_type
from xml2db.exceptions import DataModelConfigError

ORDERS_XSD = os.path.join("tests", "sample_models", "orders", "orders.xsd")


# ---------------------------------------------------------------------------
# resolve_sa_type
# ---------------------------------------------------------------------------


class TestResolveSaType:
    def test_simple_name(self):
        t = resolve_sa_type("Integer")
        assert isinstance(t, sa.Integer)

    def test_string_with_length(self):
        t = resolve_sa_type("String(100)")
        assert isinstance(t, sa.String)
        assert t.length == 100

    def test_datetime_with_kwarg(self):
        t = resolve_sa_type("DateTime(timezone=True)")
        assert isinstance(t, sa.DateTime)
        assert t.timezone is True

    def test_numeric_with_args(self):
        t = resolve_sa_type("Numeric(10, 2)")
        assert isinstance(t, sa.Numeric)
        assert t.precision == 10
        assert t.scale == 2

    def test_passthrough_sa_instance(self):
        instance = sa.String(50)
        assert resolve_sa_type(instance) is instance

    def test_passthrough_sa_class(self):
        assert resolve_sa_type(sa.Integer) is sa.Integer

    def test_unknown_type_raises(self):
        with pytest.raises(DataModelConfigError, match="Unknown SQLAlchemy type"):
            resolve_sa_type("NotAType")

    def test_malformed_string_raises(self):
        with pytest.raises(DataModelConfigError, match="Cannot parse"):
            resolve_sa_type("String(")

    def test_uuid_alias(self):
        assert isinstance(resolve_sa_type("UUID"), sa.Uuid)


# ---------------------------------------------------------------------------
# parse_yaml_config
# ---------------------------------------------------------------------------


class TestParseYamlConfig:
    def test_empty_string_returns_empty_dict(self):
        assert parse_yaml_config("") == {}

    def test_none_yaml_returns_empty_dict(self):
        assert parse_yaml_config("# just a comment\n") == {}

    def test_valid_config(self):
        yaml = textwrap.dedent("""\
            row_numbers: true
            tables:
              shiporder:
                reuse: false
                fields:
                  orderid:
                    type: String(50)
                    rename: order_id
        """)
        cfg = parse_yaml_config(yaml)
        assert cfg["row_numbers"] is True
        assert cfg["tables"]["shiporder"]["reuse"] is False
        assert cfg["tables"]["shiporder"]["fields"]["orderid"]["rename"] == "order_id"

    def test_non_mapping_raises(self):
        with pytest.raises(DataModelConfigError, match="mapping"):
            parse_yaml_config("- item1\n- item2\n")

    def test_callable_key_rejected(self):
        for key in ("document_tree_hook", "document_tree_node_hook", "record_hash_constructor"):
            with pytest.raises(DataModelConfigError, match="callable"):
                parse_yaml_config(f"{key}: something\n")

    def test_metadata_columns_type_must_be_string(self):
        yaml = textwrap.dedent("""\
            metadata_columns:
              - name: col1
                type: 123
        """)
        with pytest.raises(DataModelConfigError, match="must be a string"):
            parse_yaml_config(yaml)

    def test_metadata_columns_string_type_accepted(self):
        yaml = textwrap.dedent("""\
            metadata_columns:
              - name: col1
                type: String(256)
        """)
        cfg = parse_yaml_config(yaml)
        assert cfg["metadata_columns"][0]["type"] == "String(256)"

    def test_field_type_must_be_string(self):
        yaml = textwrap.dedent("""\
            tables:
              t:
                fields:
                  f:
                    type: 42
        """)
        with pytest.raises(DataModelConfigError, match="must be a string"):
            parse_yaml_config(yaml)


# ---------------------------------------------------------------------------
# Top-level transform option
# ---------------------------------------------------------------------------


class TestGlobalTransformOption:
    def _make_model(self, config):
        return DataModel(xsd_file=ORDERS_XSD, model_config=config)

    def test_default_elevates_orderperson(self):
        m = self._make_model({})
        # With default (auto), orderperson is elevated into shipordertype
        assert "orderperson" not in m.tables["shipordertype"].relations_1
        assert any(c.startswith("orderperson_") for c in m.tables["shipordertype"].columns)

    def test_transform_false_keeps_relations(self):
        m = self._make_model({"transform": False})
        # With transform:false, orderperson stays as a child relation
        assert "orderperson" in m.tables["shipordertype"].relations_1
        assert not any(c.startswith("orderperson_") for c in m.tables["shipordertype"].columns)

    def test_transform_false_keeps_more_tables(self):
        m_auto = self._make_model({})
        m_off = self._make_model({"transform": False})
        # No elevation means child tables are not absorbed
        assert len(m_off.tables) > len(m_auto.tables)

    def test_transform_auto_string_same_as_default(self):
        m_default = self._make_model({})
        m_auto = self._make_model({"transform": "auto"})
        assert list(m_auto.tables["shipordertype"].columns.keys()) == \
               list(m_default.tables["shipordertype"].columns.keys())

    def test_transform_true_same_as_default(self):
        m_default = self._make_model({})
        m_true = self._make_model({"transform": True})
        assert list(m_true.tables["shipordertype"].columns.keys()) == \
               list(m_default.tables["shipordertype"].columns.keys())

    def test_invalid_transform_value_raises(self):
        with pytest.raises(DataModelConfigError, match="Invalid 'transform'"):
            self._make_model({"transform": "none"})

    def test_transform_false_per_field_auto_overrides_global(self):
        # Global false but explicit per-field "auto" should restore default elevation
        m_off = self._make_model({"transform": False})
        m_field_auto = self._make_model({
            "transform": False,
            "tables": {"shiporder": {"fields": {"orderperson": {"transform": "auto"}}}},
        })
        # With global false, orderperson is a relation
        assert "orderperson" in m_off.tables["shipordertype"].relations_1
        # With field-level auto override, orderperson is elevated again
        assert "orderperson" not in m_field_auto.tables["shipordertype"].relations_1
        assert any(
            c.startswith("orderperson_")
            for c in m_field_auto.tables["shipordertype"].columns
        )


# ---------------------------------------------------------------------------
# Field-level transform: "auto" and choice_transform: "auto"
# ---------------------------------------------------------------------------


class TestAutoTransformValue:
    def _make_model(self, config):
        return DataModel(xsd_file=ORDERS_XSD, model_config=config)

    def test_field_transform_auto_same_as_omitted(self):
        m_omit = self._make_model({})
        m_auto = self._make_model({
            "tables": {"shiporder": {"fields": {"orderperson": {"transform": "auto"}}}}
        })
        assert list(m_auto.tables["shipordertype"].columns.keys()) == \
               list(m_omit.tables["shipordertype"].columns.keys())

    def test_field_transform_auto_does_not_suppress_elevation(self):
        m = self._make_model({
            "tables": {"shiporder": {"fields": {"orderperson": {"transform": "auto"}}}}
        })
        assert "orderperson" not in m.tables["shipordertype"].relations_1

    def test_choice_transform_auto_same_as_omitted(self):
        m_omit = self._make_model({})
        m_auto = self._make_model({
            "tables": {"companyId": {"choice_transform": "auto"}}
        })
        # Both should produce the same set of tables
        assert set(m_auto.tables.keys()) == set(m_omit.tables.keys())
