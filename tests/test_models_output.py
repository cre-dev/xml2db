import os

import pytest
from sqlalchemy.dialects import postgresql, mssql, mysql

from xml2db import DataModel
from .sample_models import models


@pytest.mark.parametrize(
    "test_config",
    [
        {**model, **model["versions"][i], "version_id": i}
        for model in models
        for i in range(len(model["versions"]))
    ],
)
def test_model_erd(test_config):
    """A test to check if generated ERD matches saved output"""

    model = DataModel(
        test_config["xsd_path"],
        short_name=test_config["id"],
        model_config=test_config["config"],
    )

    expected = open(
        os.path.join(
            os.path.dirname(test_config["xsd_path"]),
            f"{test_config['id']}_erd_version{test_config['version_id']}.md",
        ),
        "r",
    ).read()

    actual = "```mermaid\n" + model.get_entity_rel_diagram(text_context=False) + "\n```"
    assert actual == expected


@pytest.mark.parametrize(
    "test_config",
    [
        {**model, **model["versions"][i], "version_id": i, "dialect": d.dialect()}
        for model in models
        for i in range(len(model["versions"]))
        for d in [postgresql, mssql, mysql]
    ],
)
def test_model_ddl(test_config):
    """A test to check if generated SQL DDL matches saved output"""

    model = DataModel(
        test_config["xsd_path"],
        short_name=test_config["id"],
        model_config=test_config["config"],
        db_type=test_config["dialect"].name,
    )

    expected = open(
        os.path.join(
            os.path.dirname(test_config["xsd_path"]),
            f"{test_config['id']}_ddl_{test_config['dialect'].name}_version{test_config['version_id']}.sql",
        ),
        "r",
    ).read()

    actual = "".join(
        [
            str(s.compile(dialect=test_config["dialect"]))
            for s in model.get_all_create_table_statements()
        ]
        + [
            str(s.compile(dialect=test_config["dialect"])) + "\n\n"
            for s in model.get_all_create_index_statements()
        ]
    )

    assert actual == expected
